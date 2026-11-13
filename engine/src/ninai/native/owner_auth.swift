// Fixed, bundled macOS helper. Never accepts a password or stores credentials.
import Foundation
import LocalAuthentication
import Darwin

let method = "macos_local_authentication"

func finish(_ fields: [String: Any], _ code: Int32) -> Never {
    var response = fields
    response["method"] = method
    if let data = try? JSONSerialization.data(withJSONObject: response) {
        FileHandle.standardOutput.write(data)
        FileHandle.standardOutput.write(Data("\n".utf8))
    }
    exit(code)
}

guard CommandLine.arguments.count == 2,
      ["--check", "--verify"].contains(CommandLine.arguments[1]) else {
    finish(["reason": "invalid_request"], 2)
}

let context = LAContext()
context.touchIDAuthenticationAllowableReuseDuration = 0
var policyError: NSError?
guard context.canEvaluatePolicy(.deviceOwnerAuthentication, error: &policyError) else {
    finish(["available": false, "reason": "unavailable"], 1)
}
if CommandLine.arguments[1] == "--check" {
    // canEvaluatePolicy does not present an authentication dialog.
    finish(["available": true], 0)
}

let input = FileHandle.standardInput.readDataToEndOfFile()
guard input.count <= 4096,
      let request = (try? JSONSerialization.jsonObject(with: input)) as? [String: Any],
      let reason = request["reason"] as? String,
      !reason.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
      reason.count <= 500,
      reason.unicodeScalars.allSatisfy({ !CharacterSet.controlCharacters.contains($0) }),
      let nonce = request["nonce"] as? String,
      nonce.count == 64,
      nonce.allSatisfy({ $0.isHexDigit }) else {
    finish(["reason": "invalid_request"], 2)
}

// Each helper process uses a new context, no credential injection or reuse.
context.evaluatePolicy(.deviceOwnerAuthentication, localizedReason: reason) { success, error in
    if success {
        finish(["verified": true, "nonce": nonce, "os_user_id": Int(getuid())], 0)
    }
    let code = (error as NSError?)?.code
    let cancelled = [LAError.userCancel.rawValue, LAError.appCancel.rawValue, LAError.systemCancel.rawValue]
    finish(["verified": false, "reason": code.map { cancelled.contains($0) } == true ? "cancelled" : "failed"], 1)
}

// Keep the main run loop alive for the OS prompt and cancel after one minute.
DispatchQueue.main.asyncAfter(deadline: .now() + 60) {
    context.invalidate()
    finish(["verified": false, "reason": "timeout"], 1)
}
RunLoop.main.run()
