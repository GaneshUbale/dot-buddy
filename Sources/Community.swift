// Community characters: packs people share under community/ in the GitHub repo, listed in community/index.json.
//
// Nothing here runs until you open "More Characters…" (or use --community-list / --community-install). Then the app reads
// the index from raw.githubusercontent.com, shows each pack with its preview, and on Install downloads only the files the
// index lists for that pack (chara.json and motion PNGs), checks every file's size and SHA-256 against the index, and puts
// the pack in the characters folder. A pack is plain data: the same loader and size limits as any pack you add by hand.
import AppKit
import CryptoKit

let COMMUNITY_BASE: String = {
  let e = ProcessInfo.processInfo.environment["DOTBUDDY_COMMUNITY_BASE"] ?? ""   // tests point this at a local folder (file://…/community/)
  let b = e.isEmpty ? "https://raw.githubusercontent.com/\(UPDATE_REPO)/main/community/" : e
  return b.hasSuffix("/") ? b : b + "/"
}()
/// Limits for a downloaded pack. Real packs are a few KB per file
let COMMUNITY_MAX_FILE = 256 << 10, COMMUNITY_MAX_PACK = 2 << 20, COMMUNITY_MAX_FILES = 48, COMMUNITY_MAX_INDEX = 4 << 20
/// Marker written into a pack installed from the community list (lets the window say Installed / Update, and lets an update replace it)
let COMMUNITY_MARKER = ".community.json"

struct CommunityFile { let name: String, sha256: String, size: Int }
struct CommunityPack {
  let id: String, name: String, names: [String: String], author: String, license: String, description: String
  let files: [CommunityFile], preview: String?
  var shownName: String { names[LANG.rawValue] ?? names["en"] ?? name }
  /// One value for "which version of this pack": changes whenever any file changes
  var digest: String { SHA256.hash(data: Data(files.map { "\($0.name):\($0.sha256)" }.joined(separator: "\n").utf8)).map { String(format: "%02x", $0) }.joined() }
}
enum CommunityError: Error { case network(String), bad(String), exists(String) }
func describe(_ e: CommunityError) -> String {
  switch e {
  case .network(let s): return T("인터넷 문제(\(s))", "network problem (\(s))")
  case .bad(let s): return T("받은 꾸러미가 이상해요(\(s))", "the pack looks wrong (\(s))")
  case .exists(let s): return T("캐릭터 폴더에 이미 \(s) 가 있어요(직접 넣은 것 같아요)", "your characters folder already has \(s) (one you added yourself)")
  }
}

let COMMUNITY_ID = try! NSRegularExpression(pattern: "^[a-z0-9][a-z0-9-]{1,31}$")
func validCommunityID(_ s: String) -> Bool { COMMUNITY_ID.firstMatch(in: s, range: NSRange(s.startIndex..., in: s)) != nil }
/// Only chara.json and <motion>.png may be downloaded (no paths, no other file types)
func validCommunityFile(_ s: String) -> Bool {
  if s == "chara.json" { return true }
  guard s.hasSuffix(".png") else { return false }
  return MOTIONS.contains { $0.0 + ".png" == s }
}

/// GET a URL (call off the main thread). https:// or, for tests, file://
func communityGet(_ url: URL, max: Int, timeout: Double = 30) -> Result<Data, CommunityError> {
  var req = URLRequest(url: url, timeoutInterval: timeout)
  req.setValue("DotBuddy/\(APP_VERSION)", forHTTPHeaderField: "User-Agent")
  var out: Result<Data, CommunityError> = .failure(.network("no response"))
  let done = DispatchSemaphore(value: 0)
  URLSession(configuration: .ephemeral).dataTask(with: req) { d, r, e in
    if let e { out = .failure(.network(e.localizedDescription)) }
    else if let h = r as? HTTPURLResponse, !(200..<300).contains(h.statusCode) { out = .failure(.network("HTTP \(h.statusCode)")) }
    else if let d, d.count <= max { out = .success(d) }
    else { out = .failure(.bad("too big")) }
    done.signal()
  }.resume()
  done.wait()
  return out
}

/// The community list (call off the main thread). Packs with a bad id, file name or size are left out
func communityIndex() -> Result<[CommunityPack], CommunityError> {
  guard let u = URL(string: COMMUNITY_BASE + "index.json") else { return .failure(.network("bad URL")) }
  switch communityGet(u, max: COMMUNITY_MAX_INDEX) {
  case .failure(let e): return .failure(e)
  case .success(let d):
    guard let j = try? JSONSerialization.jsonObject(with: d) as? [String: Any], let packs = j["packs"] as? [[String: Any]] else { return .failure(.bad("index.json")) }
    var out: [CommunityPack] = []
    for p in packs {
      guard let id = p["id"] as? String, validCommunityID(id), let fl = p["files"] as? [[String: Any]] else { continue }
      var files: [CommunityFile] = []
      for f in fl {
        guard let n = f["name"] as? String, validCommunityFile(n), let h = f["sha256"] as? String, h.count == 64, let s = f["size"] as? Int, s > 0, s <= COMMUNITY_MAX_FILE else { files = []; break }
        files.append(CommunityFile(name: n, sha256: h.lowercased(), size: s))
      }
      guard files.contains(where: { $0.name == "idle.png" }), files.count <= COMMUNITY_MAX_FILES, files.map(\.size).reduce(0, +) <= COMMUNITY_MAX_PACK,
            Set(files.map(\.name)).count == files.count else { continue }
      let str = { (k: String) in (p[k] as? String ?? "").trimmingCharacters(in: .whitespacesAndNewlines) }
      let preview = (p["preview"] as? String).flatMap { $0 == "preview.gif" ? $0 : nil }
      out.append(CommunityPack(id: id, name: str("name").isEmpty ? id : String(str("name").prefix(40)), names: (p["names"] as? [String: String] ?? [:]).mapValues { String($0.prefix(40)) },
                               author: String(str("author").prefix(39)), license: String(str("license").prefix(20)), description: String(str("description").prefix(140)), files: files, preview: preview))
    }
    return .success(out)
  }
}

enum CommunityState { case notInstalled, installed, updatable, mine }
/// Is this pack in the characters folder, and is it the version the list has?
func communityState(_ p: CommunityPack, dir: URL = CHARAS_DIR) -> CommunityState {
  let d = dir.appendingPathComponent(p.id)
  guard FileManager.default.fileExists(atPath: d.path) else { return .notInstalled }
  guard let m = try? Data(contentsOf: d.appendingPathComponent(COMMUNITY_MARKER)), let j = try? JSONSerialization.jsonObject(with: m) as? [String: Any] else { return .mine }
  return j["digest"] as? String == p.digest ? .installed : .updatable
}

/// Download one pack into the characters folder (call off the main thread). Returns the character id ("pack:<id>")
func installCommunityPack(_ p: CommunityPack, dir: URL = CHARAS_DIR) -> Result<String, CommunityError> {
  let fm = FileManager.default
  guard validCommunityID(p.id) else { return .failure(.bad("id")) }
  if communityState(p, dir: dir) == .mine { return .failure(.exists(p.id)) }
  var got: [(String, Data)] = []
  for f in p.files {
    guard validCommunityFile(f.name), let u = URL(string: COMMUNITY_BASE + p.id + "/" + f.name) else { return .failure(.bad(f.name)) }
    switch communityGet(u, max: COMMUNITY_MAX_FILE) {
    case .failure(let e): return .failure(e)
    case .success(let d):
      let h = SHA256.hash(data: d).map { String(format: "%02x", $0) }.joined()
      guard d.count == f.size, h == f.sha256 else { return .failure(.bad("\(f.name) doesn't match the list")) }
      got.append((f.name, d))
    }
  }
  try? fm.createDirectory(at: dir, withIntermediateDirectories: true)
  let tmp = dir.appendingPathComponent(".incoming-\(UUID().uuidString)"), dst = dir.appendingPathComponent(p.id)
  defer { try? fm.removeItem(at: tmp) }
  do {
    try fm.createDirectory(at: tmp, withIntermediateDirectories: true)
    for (n, d) in got { try d.write(to: tmp.appendingPathComponent(n)) }
    let marker: [String: Any] = ["id": p.id, "digest": p.digest, "author": p.author, "license": p.license, "source": COMMUNITY_BASE + p.id + "/"]
    try JSONSerialization.data(withJSONObject: marker, options: [.sortedKeys]).write(to: tmp.appendingPathComponent(COMMUNITY_MARKER))
    if fm.fileExists(atPath: dst.path) { try fm.removeItem(at: dst) }         // only a pack we installed before (checked above)
    try fm.moveItem(at: tmp, to: dst)
  } catch { return .failure(.bad(error.localizedDescription)) }
  // The pack must load like any other; if it doesn't, take it out again
  guard loadCharas(in: dir).contains(where: { $0.id == "pack:" + p.id }) else { try? fm.removeItem(at: dst); return .failure(.bad("it doesn't load")) }
  return .success("pack:" + p.id)
}

// ---------- The window ----------
final class CommunityWindow: NSObject, NSWindowDelegate {
  let window: NSWindow
  private let stack = NSStackView(), status = NSTextField(labelWithString: "")
  private var packs: [CommunityPack] = []
  private var busy = false
  private let onInstalled: (String, String) -> Void                          // (character id, shown name)
  var onClose: (() -> Void)?

  init(onInstalled: @escaping (String, String) -> Void) {
    self.onInstalled = onInstalled
    window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 480, height: 520), styleMask: [.titled, .closable, .resizable], backing: .buffered, defer: false)
    super.init()
    window.title = T("다른 캐릭터 받기", "More Characters")
    window.isReleasedWhenClosed = false; window.delegate = self; window.minSize = NSSize(width: 400, height: 300)
    let head = NSTextField(wrappingLabelWithString: T("사람들이 그려서 올린 캐릭터예요. 받으면 캐릭터 메뉴에 바로 생겨요. 내 캐릭터를 올리는 방법은 아래 링크에 있어요.",
                                                     "Characters people drew and shared. Install one and it shows up in the Character menu right away. To share yours, see the link below."))
    head.font = .systemFont(ofSize: 12); head.textColor = .secondaryLabelColor
    let link = NSButton(title: "", target: self, action: #selector(openGuide)); link.isBordered = false
    link.attributedTitle = NSAttributedString(string: T("내 캐릭터 올리는 법 →", "How to share your character →"), attributes: [.foregroundColor: NSColor.linkColor, .font: NSFont.systemFont(ofSize: 12)])
    stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 0
    let doc = FlippedView(); doc.translatesAutoresizingMaskIntoConstraints = false; doc.addSubview(stack)
    stack.translatesAutoresizingMaskIntoConstraints = false
    let scroll = NSScrollView(); scroll.hasVerticalScroller = true; scroll.drawsBackground = false; scroll.documentView = doc; scroll.translatesAutoresizingMaskIntoConstraints = false
    status.textColor = .secondaryLabelColor; status.font = .systemFont(ofSize: 12)
    let root = NSView(); [head, link, scroll, status].forEach { $0.translatesAutoresizingMaskIntoConstraints = false; root.addSubview($0) }
    NSLayoutConstraint.activate([
      head.topAnchor.constraint(equalTo: root.topAnchor, constant: 14), head.leadingAnchor.constraint(equalTo: root.leadingAnchor, constant: 16), head.trailingAnchor.constraint(equalTo: root.trailingAnchor, constant: -16),
      link.topAnchor.constraint(equalTo: head.bottomAnchor, constant: 4), link.leadingAnchor.constraint(equalTo: head.leadingAnchor),
      scroll.topAnchor.constraint(equalTo: link.bottomAnchor, constant: 10), scroll.leadingAnchor.constraint(equalTo: root.leadingAnchor), scroll.trailingAnchor.constraint(equalTo: root.trailingAnchor),
      status.topAnchor.constraint(equalTo: scroll.bottomAnchor, constant: 8), status.leadingAnchor.constraint(equalTo: head.leadingAnchor), status.trailingAnchor.constraint(equalTo: head.trailingAnchor),
      status.bottomAnchor.constraint(equalTo: root.bottomAnchor, constant: -10),
      doc.leadingAnchor.constraint(equalTo: scroll.contentView.leadingAnchor), doc.trailingAnchor.constraint(equalTo: scroll.contentView.trailingAnchor), doc.topAnchor.constraint(equalTo: scroll.contentView.topAnchor),
      stack.leadingAnchor.constraint(equalTo: doc.leadingAnchor, constant: 16), stack.trailingAnchor.constraint(equalTo: doc.trailingAnchor, constant: -16),
      stack.topAnchor.constraint(equalTo: doc.topAnchor), stack.bottomAnchor.constraint(equalTo: doc.bottomAnchor, constant: -8),
    ])
    window.contentView = root
    window.center()
  }
  func show() {
    NSApp.activate(ignoringOtherApps: true); window.makeKeyAndOrderFront(nil)
    load()
  }
  func windowWillClose(_ n: Notification) { onClose?() }
  @objc func openGuide() { NSWorkspace.shared.open(URL(string: "https://github.com/\(UPDATE_REPO)/tree/main/community#readme")!) }

  private func load() {
    status.stringValue = T("목록 받는 중…", "Loading the list…")
    DispatchQueue.global(qos: .userInitiated).async { [weak self] in
      let r = communityIndex()
      DispatchQueue.main.async {
        guard let self else { return }
        switch r {
        case .failure(let e): self.status.stringValue = T("목록을 못 받았어요: ", "Couldn't load the list: ") + describe(e)
        case .success(let p): self.packs = p; self.rebuild(); self.status.stringValue = T("캐릭터 \(p.count)개", p.count == 1 ? "1 character" : "\(p.count) characters")
        }
      }
    }
  }
  private func rebuild() {
    stack.arrangedSubviews.forEach { $0.removeFromSuperview() }
    for (i, p) in packs.enumerated() {
      if i > 0 { let sep = NSBox(); sep.boxType = .separator; stack.addArrangedSubview(sep); sep.widthAnchor.constraint(equalTo: stack.widthAnchor).isActive = true }
      let row = self.row(p); stack.addArrangedSubview(row); row.widthAnchor.constraint(equalTo: stack.widthAnchor).isActive = true
    }
  }
  private func row(_ p: CommunityPack) -> NSView {
    let img = NSImageView(); img.imageScaling = .scaleProportionallyUpOrDown; img.animates = true; img.wantsLayer = true
    img.layer?.magnificationFilter = .nearest; img.layer?.cornerRadius = 6; img.layer?.backgroundColor = NSColor(white: 0.5, alpha: 0.08).cgColor
    if let pv = p.preview, let u = URL(string: COMMUNITY_BASE + p.id + "/" + pv) {
      DispatchQueue.global(qos: .utility).async {
        if case .success(let d) = communityGet(u, max: 1 << 20), let im = NSImage(data: d) { DispatchQueue.main.async { img.image = im } }
      }
    }
    let name = NSTextField(labelWithString: p.shownName); name.font = .boldSystemFont(ofSize: 13)
    let by = NSTextField(labelWithString: [p.author.isEmpty ? "" : T("그린 사람 \(p.author)", "by \(p.author)"), p.license].filter { !$0.isEmpty }.joined(separator: " · "))
    by.font = .systemFont(ofSize: 11); by.textColor = .secondaryLabelColor
    let desc = NSTextField(wrappingLabelWithString: p.description); desc.font = .systemFont(ofSize: 12)
    let state = communityState(p)
    let btn = NSButton(title: "", target: self, action: #selector(install(_:))); btn.bezelStyle = .rounded; btn.identifier = NSUserInterfaceItemIdentifier(p.id)
    switch state {
    case .notInstalled: btn.title = T("받기", "Install")
    case .updatable: btn.title = T("새로 받기", "Update")
    case .installed: btn.title = T("받음", "Installed"); btn.isEnabled = false
    case .mine: btn.title = T("이름 겹침", "Name in use"); btn.isEnabled = false; btn.toolTip = describe(.exists(p.id))
    }
    let text = NSStackView(views: [name, by] + (p.description.isEmpty ? [] : [desc])); text.orientation = .vertical; text.alignment = .leading; text.spacing = 2
    let h = NSStackView(views: [img, text, btn]); h.orientation = .horizontal; h.alignment = .centerY; h.distribution = .fill; h.spacing = 12; h.edgeInsets = NSEdgeInsets(top: 10, left: 0, bottom: 10, right: 0)
    img.widthAnchor.constraint(equalToConstant: 96).isActive = true; img.heightAnchor.constraint(equalToConstant: 64).isActive = true
    text.setContentHuggingPriority(.defaultLow, for: .horizontal); text.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
    btn.setContentHuggingPriority(.required, for: .horizontal); img.setContentHuggingPriority(.required, for: .horizontal)
    desc.preferredMaxLayoutWidth = 240
    return h
  }
  @objc func install(_ b: NSButton) {
    guard !busy, let id = b.identifier?.rawValue, let p = packs.first(where: { $0.id == id }) else { return }
    busy = true; b.isEnabled = false; b.title = T("받는 중…", "Installing…")
    DispatchQueue.global(qos: .userInitiated).async { [weak self] in
      let r = installCommunityPack(p)
      DispatchQueue.main.async {
        guard let self else { return }
        self.busy = false
        switch r {
        case .success(let cid): self.status.stringValue = T("\(p.shownName) 받았어요", "Installed \(p.shownName)"); self.onInstalled(cid, p.shownName)
        case .failure(let e): self.status.stringValue = T("못 받았어요: ", "Couldn't install: ") + describe(e)
        }
        self.rebuild()
      }
    }
  }
}
private final class FlippedView: NSView { override var isFlipped: Bool { true } }
