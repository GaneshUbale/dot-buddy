// Self-update from GitHub Releases, with no third-party framework.
//
// Release side (CI): the zip is signed with an Ed25519 key kept in the repo secret UPDATE_SIGNING_KEY, and the signature
// (base64) is uploaded next to it as <zip>.sig. App side: find the latest release tag on github.com, compare versions,
// download the zip and its .sig, verify the signature against the public key below, check the bundle inside
// (bundle id, version, code signature), then swap it in place of the running app and relaunch.
//
// Network use is opt-in: the app only talks to GitHub when automatic checks are turned on (asked once on first launch,
// toggled in the menu) or when you choose "Check for Updates" yourself. Nothing but the app version (User-Agent) is sent.
// Builds made from source (build.sh without BUILD_KIND=release) never replace themselves; they only say a new version exists.
import AppKit
import CryptoKit

let UPDATE_REPO = "doldoldol21/dot-buddy"
let UPDATE_PUBLIC_KEY = "+p0c918w8SdmzAoRqYqOnPlaaz9DxZsbScurt1vKhp0="

var APP_VERSION: String { Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.0.0" }
/// "release" for the zips CI publishes, "source" for local builds (they update with git pull + build.sh)
var BUILD_KIND: String { Bundle.main.infoDictionary?["DotBuddyBuild"] as? String ?? "source" }

/// Numeric version compare: "0.10.0" > "0.9.3". Non-numeric parts count as 0
func versionNewer(_ a: String, than b: String) -> Bool {
  func parts(_ v: String) -> [Int] { v.trimmingCharacters(in: CharacterSet(charactersIn: "vV")).split(separator: ".").map { Int($0.prefix { $0.isNumber }) ?? 0 } }
  let x = parts(a), y = parts(b)
  for i in 0..<max(x.count, y.count) { let p = i < x.count ? x[i] : 0, q = i < y.count ? y[i] : 0; if p != q { return p > q } }
  return false
}

/// Is `sig` (base64) a valid Ed25519 signature of `data` under `key` (base64 raw public key)?
func verifyUpdate(_ data: Data, sig: String, key: String = UPDATE_PUBLIC_KEY) -> Bool {
  guard let k = Data(base64Encoded: key), let pub = try? Curve25519.Signing.PublicKey(rawRepresentation: k),
        let s = Data(base64Encoded: sig.trimmingCharacters(in: .whitespacesAndNewlines)) else { return false }
  return pub.isValidSignature(s, for: data)
}

struct UpdateInfo { let version: String, zip: URL, sig: URL, page: URL? }
enum UpdateError: Error { case network(String), noAsset, badSignature, badBundle(String), notWritable(String), install(String) }

private func fetch(_ url: URL, timeout: Double = 30, head: Bool = false) -> Result<(Data, URL?), UpdateError> {
  var req = URLRequest(url: url, timeoutInterval: timeout)
  req.setValue("DotBuddy/\(APP_VERSION)", forHTTPHeaderField: "User-Agent")
  if head { req.httpMethod = "HEAD" }
  var out: Result<(Data, URL?), UpdateError> = .failure(.network("no response"))
  let done = DispatchSemaphore(value: 0)
  URLSession(configuration: .ephemeral).dataTask(with: req) { d, r, e in         // ephemeral: no cookies, no cache on disk
    if let e { out = .failure(.network(e.localizedDescription)) }
    else if let h = r as? HTTPURLResponse, !(200..<300).contains(h.statusCode) { out = .failure(h.statusCode == 404 ? .noAsset : .network("HTTP \(h.statusCode)")) }
    else { out = .success((d ?? Data(), r?.url)) }
    done.signal()
  }.resume()
  done.wait()
  return out
}

/// The latest published release (call off the main thread). Uses github.com's /releases/latest redirect, not the REST API:
/// the API allows only 60 anonymous calls an hour per IP, which a shared office network runs out of
func latestRelease() -> Result<UpdateInfo, UpdateError> {
  let base = ProcessInfo.processInfo.environment["DOTBUDDY_UPDATE_BASE"].flatMap { $0.isEmpty ? nil : $0 } ?? "https://github.com/\(UPDATE_REPO)"
  guard let latest = URL(string: base + "/releases/latest") else { return .failure(.network("bad URL")) }
  switch fetch(latest, head: true) {
  case .failure(let e): return .failure(e)
  case .success(let (_, final)):
    guard let f = final, f.path.contains("/releases/tag/") else { return .failure(.noAsset) }   // no release yet: it stays on /releases
    let tag = f.lastPathComponent, v = tag.trimmingCharacters(in: CharacterSet(charactersIn: "vV"))
    guard !v.isEmpty, v.first!.isNumber, let zip = URL(string: "\(base)/releases/download/\(tag)/Dot-Buddy-\(v).zip"),
          let sig = URL(string: "\(base)/releases/download/\(tag)/Dot-Buddy-\(v).zip.sig") else { return .failure(.noAsset) }
    return .success(UpdateInfo(version: v, zip: zip, sig: sig, page: f))
  }
}

private func sh(_ exe: String, _ args: [String]) -> Bool {
  let p = Process(); p.executableURL = URL(fileURLWithPath: exe); p.arguments = args
  p.standardOutput = FileHandle.nullDevice; p.standardError = FileHandle.nullDevice
  guard (try? p.run()) != nil else { return false }
  p.waitUntilExit(); return p.terminationStatus == 0
}

/// Download, verify and swap in the new app at `appPath` (call off the main thread). Returns the installed path.
/// The old bundle goes to the Trash, so a bad update can be undone by hand.
func installUpdate(_ u: UpdateInfo, appPath: String = Bundle.main.bundlePath) -> Result<String, UpdateError> {
  let fm = FileManager.default
  let parent = (appPath as NSString).deletingLastPathComponent
  guard fm.isWritableFile(atPath: parent) else { return .failure(.notWritable(parent)) }
  let sigData: Data, zip: Data
  switch fetch(u.sig) { case .success(let r): sigData = r.0; case .failure(let e): return .failure(e) }   // the signature first: a release without one is never downloaded
  switch fetch(u.zip, timeout: 300) { case .success(let r): zip = r.0; case .failure(let e): return .failure(e) }
  guard verifyUpdate(zip, sig: String(decoding: sigData, as: UTF8.self)) else { return .failure(.badSignature) }

  let work = fm.temporaryDirectory.appendingPathComponent("dotbuddy-update-\(UUID().uuidString)")
  defer { try? fm.removeItem(at: work) }
  try? fm.createDirectory(at: work, withIntermediateDirectories: true)
  let zipURL = work.appendingPathComponent("u.zip")
  guard (try? zip.write(to: zipURL)) != nil, sh("/usr/bin/ditto", ["-x", "-k", zipURL.path, work.appendingPathComponent("x").path]) else { return .failure(.install("unzip")) }
  guard let app = (try? fm.contentsOfDirectory(at: work.appendingPathComponent("x"), includingPropertiesForKeys: nil))?.first(where: { $0.pathExtension == "app" }) else { return .failure(.badBundle("no .app in the zip")) }
  let info = NSDictionary(contentsOf: app.appendingPathComponent("Contents/Info.plist")) as? [String: Any] ?? [:]
  guard info["CFBundleIdentifier"] as? String == BUNDLE_ID else { return .failure(.badBundle("bundle id \(info["CFBundleIdentifier"] ?? "?")")) }
  guard info["CFBundleShortVersionString"] as? String == u.version else { return .failure(.badBundle("version \(info["CFBundleShortVersionString"] ?? "?")")) }
  guard sh("/usr/bin/codesign", ["--verify", "--deep", "--strict", app.path]) else { return .failure(.badBundle("code signature")) }
  _ = sh("/usr/bin/xattr", ["-dr", "com.apple.quarantine", app.path])               // we verified it ourselves; don't make the user approve it again

  // Swap: move the new app next to the old one, then trade places. If anything fails, put the old one back
  let staged = URL(fileURLWithPath: parent).appendingPathComponent(".DotBuddy-update-\(u.version).app"), old = URL(fileURLWithPath: appPath)
  try? fm.removeItem(at: staged)
  guard (try? fm.moveItem(at: app, to: staged)) != nil else { return .failure(.install("stage")) }
  var trashed: NSURL?
  do { try fm.trashItem(at: old, resultingItemURL: &trashed) } catch { try? fm.removeItem(at: staged); return .failure(.install("could not move the old app to the Trash")) }
  do { try fm.moveItem(at: staged, to: old) } catch {
    if let t = trashed as URL? { try? fm.moveItem(at: t, to: old) }
    return .failure(.install("could not put the new app in place"))
  }
  return .success(old.path)
}

/// Quit and open the (new) app at the same path
func relaunch(_ path: String = Bundle.main.bundlePath) {
  let p = Process(); p.executableURL = URL(fileURLWithPath: "/bin/sh")
  p.arguments = ["-c", "sleep 1; /usr/bin/open -n \"$0\"", path]
  try? p.run()
  NSApp.terminate(nil)
}

func describe(_ e: UpdateError) -> String {
  switch e {
  case .network(let s): return T("인터넷 문제(\(s))", "network problem (\(s))")
  case .noAsset: return T("새 판에 서명된 파일이 없어요", "the release has no signed download")
  case .badSignature: return T("서명이 맞지 않아요", "the signature doesn't match")
  case .badBundle(let s): return T("받은 앱이 이상해요(\(s))", "the downloaded app looks wrong (\(s))")
  case .notWritable(let p): return T("\(p) 에 쓸 수 없어요", "can't write to \(p)")
  case .install(let s): return T("설치 실패(\(s))", "install failed (\(s))")
  }
}
