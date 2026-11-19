// Language: on-screen text (menus, bubbles, mutterings, CLI help) comes in two versions, Korean and English. There is no dictionary file; English sits next to the Korean in the code.
// Order of choice: DOTBUDDY_LANG (ko|en) → the choice made in the menu (UserDefaults "lang") → first system language (ko if Korean, else en)
import Foundation

enum Lang: String { case ko, en }
let LANG: Lang = {
  if let e = ProcessInfo.processInfo.environment["DOTBUDDY_LANG"], let l = Lang(rawValue: e) { return l }
  if let s = UserDefaults.standard.string(forKey: "lang"), let l = Lang(rawValue: s) { return l }
  return (Locale.preferredLanguages.first ?? "en").hasPrefix("ko") ? .ko : .en
}()
/// Two languages of one phrase — T("<Korean text>", "Done!")
func T(_ ko: String, _ en: String) -> String { LANG == .ko ? ko : en }
/// Two languages of a set of phrases to pick from — T(["<Korean 1>", "<Korean 2>"], ["hi", "hey there"]). The two sets may differ in size
func T(_ ko: [String], _ en: [String]) -> [String] { LANG == .ko ? ko : en }
