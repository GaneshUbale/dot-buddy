// Sign a release zip for the in-app updater: prints the base64 Ed25519 signature of the file.
//   UPDATE_SIGNING_KEY=<base64 raw private key> swift scripts/sign-update.swift Dot-Buddy-1.2.3.zip > Dot-Buddy-1.2.3.zip.sig
// The matching public key is UPDATE_PUBLIC_KEY in Sources/Update.swift.
import CryptoKit
import Foundation

guard CommandLine.arguments.count == 2, let b64 = ProcessInfo.processInfo.environment["UPDATE_SIGNING_KEY"],
      let raw = Data(base64Encoded: b64.trimmingCharacters(in: .whitespacesAndNewlines)),
      let key = try? Curve25519.Signing.PrivateKey(rawRepresentation: raw),
      let data = FileManager.default.contents(atPath: CommandLine.arguments[1]) else {
  FileHandle.standardError.write("usage: UPDATE_SIGNING_KEY=… swift scripts/sign-update.swift <file>\n".data(using: .utf8)!)
  exit(2)
}
print(try key.signature(for: data).base64EncodedString())
