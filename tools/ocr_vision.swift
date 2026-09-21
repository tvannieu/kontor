// ocr_vision.swift - OCR the pages of a PDF with Apple's Vision framework.
//
// macOS only: it depends on PDFKit and Vision, which exist only on Apple
// platforms. No third-party packages, no network access; recognition runs
// locally.
//
// Usage:
//     swift ocr_vision.swift file.pdf              # all pages
//     swift ocr_vision.swift file.pdf 3            # page 3 to the end
//     swift ocr_vision.swift file.pdf 3 5          # pages 3 to 5
//
// Output: plain text on stdout, one block per page, introduced by a line
// "===== PAGE n =====". Errors go to stderr; exit status 1 if the PDF cannot
// be opened.
//
// Requirements: macOS 10.15 or newer with the Xcode command line tools
// (`xcode-select --install`). For repeated use, compile once with
// `swiftc -O ocr_vision.swift -o ocr_vision`.
//
// Recognition languages are set below (German and English); change the
// `recognitionLanguages` line for other languages. Pages are rendered at 2x
// before recognition, which is a good trade-off between speed and accuracy
// for scanned letters.

import Foundation
import PDFKit
import Vision
import CoreGraphics

let args = CommandLine.arguments
guard args.count >= 2, let doc = PDFDocument(url: URL(fileURLWithPath: args[1])) else {
    FileHandle.standardError.write("cannot open pdf\n".data(using: .utf8)!)
    exit(1)
}
let first = args.count > 2 ? Int(args[2]) ?? 1 : 1
let last  = args.count > 3 ? Int(args[3]) ?? doc.pageCount : doc.pageCount

for i in (max(first, 1) - 1)..<min(last, doc.pageCount) {
    guard let page = doc.page(at: i) else { continue }
    let rect = page.bounds(for: .mediaBox)
    let scale: CGFloat = 2.0
    let w = Int(rect.width * scale), h = Int(rect.height * scale)
    guard let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8,
                              bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(),
                              bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { continue }
    // White background, then draw the page on top of it.
    ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
    ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
    ctx.scaleBy(x: scale, y: scale)
    page.draw(with: .mediaBox, to: ctx)
    guard let img = ctx.makeImage() else { continue }

    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["de-DE", "en-US"]
    req.usesLanguageCorrection = true
    let handler = VNImageRequestHandler(cgImage: img, options: [:])
    try? handler.perform([req])
    print("===== PAGE \(i + 1) =====")
    if let obs = req.results {
        for o in obs { if let c = o.topCandidates(1).first { print(c.string) } }
    }
}
