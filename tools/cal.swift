// cal.swift - list calendar events in a date range, via EventKit.
//
// macOS only. Reading events through AppleScript (`every event whose start
// date >= ...`) times out on large synced calendars: `whose` over a date field
// sends every event through the Apple Events bridge one at a time. EventKit
// queries a real date index, so the same range over every calendar returns in
// seconds regardless of calendar size, and recurring events come back as
// individual occurrences.
//
// Read only. To create an event, AppleScript is still the right tool: no
// search is involved, so it is not slow.
//
// Usage:
//     swift cal.swift 2026-10-06 2026-10-10     # both days inclusive
//
// Output: one line per event, sorted by start,
//     <weekday DD.MM. HH:mm> [all day] | <calendar> | <title> [| @ <location>]
//
// The first run may trigger macOS's calendar-access prompt for the terminal.
// Exit status 1 if access is denied, 2 on bad arguments.
//
// Requirements: macOS 10.15 or newer with the Xcode command line tools. For
// repeated use, compile once with `swiftc -O cal.swift -o cal`.

import EventKit
import Foundation

let store = EKEventStore()
let sem = DispatchSemaphore(value: 0)
var granted = false
if #available(macOS 14.0, *) {
    store.requestFullAccessToEvents { g, _ in granted = g; sem.signal() }
} else {
    store.requestAccess(to: .event) { g, _ in granted = g; sem.signal() }
}
sem.wait()
guard granted else {
    FileHandle.standardError.write("no calendar access\n".data(using: .utf8)!)
    exit(1)
}

let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("usage: cal.swift YYYY-MM-DD YYYY-MM-DD\n".data(using: .utf8)!)
    exit(2)
}
let df = DateFormatter(); df.dateFormat = "yyyy-MM-dd"; df.timeZone = .current
guard let start = df.date(from: args[1]), let endDay = df.date(from: args[2]) else {
    FileHandle.standardError.write("dates must look like 2026-10-06\n".data(using: .utf8)!)
    exit(2)
}
let end = endDay.addingTimeInterval(86400)  // make the end day inclusive

let pred = store.predicateForEvents(withStart: start, end: end, calendars: nil)
let events = store.events(matching: pred).sorted { $0.startDate < $1.startDate }
let out = DateFormatter(); out.dateFormat = "EEE dd.MM. HH:mm"; out.locale = .current
for e in events {
    let allDay = e.isAllDay ? " [all day]" : ""
    let loc = (e.location?.isEmpty == false) ? " | @ \(e.location!)" : ""
    print("\(out.string(from: e.startDate))\(allDay) | \(e.calendar.title) | \(e.title ?? "")\(loc)")
}
