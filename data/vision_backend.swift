// Local Vision feature-print index used by the Python search service.
// Usage: swift data/vision_backend.swift data/products.json
import Foundation
import Vision
import Darwin

func featurePrint(_ url: URL) throws -> VNFeaturePrintObservation {
    let request = VNGenerateImageFeaturePrintRequest()
    request.imageCropAndScaleOption = .scaleFit
    try VNImageRequestHandler(url: url, options: [:]).perform([request])
    guard let result = request.results?.first else {
        throw NSError(domain: "VisionBackend", code: 1,
                      userInfo: [NSLocalizedDescriptionKey: "No feature print for \(url.path)"])
    }
    return result
}

func recognizedText(_ url: URL) throws -> [String] {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    try VNImageRequestHandler(url: url, options: [:]).perform([request])
    return (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }
}

func send(_ value: [String: Any]) {
    if let data = try? JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]),
       let line = String(data: data, encoding: .utf8) {
        print(line)
        fflush(stdout)
    }
}

guard CommandLine.arguments.count == 2 else {
    fputs("Expected path to product catalog JSON\n", stderr)
    exit(2)
}

do {
    let catalogURL = URL(fileURLWithPath: CommandLine.arguments[1])
    let base = catalogURL.deletingLastPathComponent()
    let raw = try Data(contentsOf: catalogURL)
    guard let products = try JSONSerialization.jsonObject(with: raw) as? [[String: Any]] else {
        throw NSError(domain: "VisionBackend", code: 2,
                      userInfo: [NSLocalizedDescriptionKey: "Invalid product catalog"])
    }
    var gallery: [(id: String, print: VNFeaturePrintObservation)] = []
    for product in products {
        guard let image = product["image"] as? String,
              let identifier = product["id"] else { continue }
        let id = String(describing: identifier)
        let url = base.appendingPathComponent(image)
        gallery.append((id, try featurePrint(url)))
    }
    while let line = readLine(strippingNewline: true) {
        do {
            guard let data = line.data(using: .utf8),
                  let request = try JSONSerialization.jsonObject(with: data) as? [String: String],
                  let path = request["image_path"] else {
                throw NSError(domain: "VisionBackend", code: 3,
                              userInfo: [NSLocalizedDescriptionKey: "Invalid image request"])
            }
            let query = try featurePrint(URL(fileURLWithPath: path))
            let text = try recognizedText(URL(fileURLWithPath: path))
            var distances: [String: Double] = [:]
            for product in gallery {
                var distance: Float = 0
                try query.computeDistance(&distance, to: product.print)
                distances[product.id] = Double(distance)
            }
            send(["distances": distances, "recognized_text": text])
        } catch {
            send(["error": error.localizedDescription])
        }
    }
} catch {
    fputs("Vision index failed: \(error)\n", stderr)
    exit(1)
}
