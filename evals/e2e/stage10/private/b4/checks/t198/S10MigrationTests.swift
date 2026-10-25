// Hidden check for t198 (stage 10): one-time Core Data -> SwiftData migration on first start.
import CoreData
import SwiftData
import XCTest
@testable import HabitTracker

private struct Seed {
    let id: UUID
    let name: String
    let created: Date
    let streak: Int
    let archived: Bool
    let checkIns: [(UUID, Date, String?)]
}

@MainActor
final class S10MigrationTests: XCTestCase {
    private func seeds() -> [Seed] {
        let d = { (s: Double) in Date(timeIntervalSince1970: 1_700_000_000 + s) }
        return [
            Seed(id: UUID(), name: "Read", created: d(0), streak: 0, archived: false, checkIns: []),
            Seed(id: UUID(), name: "Run", created: d(100), streak: 5, archived: false,
                 checkIns: [(UUID(), d(86_400), "5k"), (UUID(), d(172_800), nil)]),
            Seed(id: UUID(), name: "Stretch", created: d(200), streak: 12, archived: true,
                 checkIns: (0..<5).map { (UUID(), d(Double($0) * 86_400 + 300), $0 % 2 == 0 ? "am" : nil) }),
        ]
    }

    private func coreData(_ seeds: [Seed]) throws -> CoreDataStack {
        let stack = CoreDataStack(inMemory: true)
        let ctx = stack.viewContext
        for s in seeds {
            let h = NSEntityDescription.insertNewObject(forEntityName: "HabitEntity", into: ctx)
            h.setValue(s.id, forKey: "id")
            h.setValue(s.name, forKey: "name")
            h.setValue(s.created, forKey: "createdAt")
            h.setValue(Int64(s.streak), forKey: "streakCount")
            h.setValue(s.archived, forKey: "archived")
            for (cid, date, note) in s.checkIns {
                let c = NSEntityDescription.insertNewObject(forEntityName: "CheckInEntity", into: ctx)
                c.setValue(cid, forKey: "id")
                c.setValue(date, forKey: "date")
                c.setValue(note, forKey: "note")
                c.setValue(h, forKey: "habit")
            }
        }
        try ctx.save()
        return stack
    }

    private func container() throws -> ModelContainer {
        try ModelContainer(for: Habit.self, CheckIn.self, configurations: ModelConfiguration(isStoredInMemoryOnly: true))
    }

    private func defaults() -> UserDefaults {
        UserDefaults(suiteName: "s10-\(UUID().uuidString)")!
    }

    /// Reads through a fresh context, so only saved data counts.
    private func habits(_ c: ModelContainer) throws -> [Habit] {
        try ModelContext(c).fetch(FetchDescriptor<Habit>())
    }

    private func checkIns(_ c: ModelContainer) throws -> [CheckIn] {
        try ModelContext(c).fetch(FetchDescriptor<CheckIn>())
    }

    func testCopiesHabitsCheckInsAndStreaks() throws {
        let s = seeds()
        let c = try container()
        try AppStartup.run(coreData: try coreData(s), container: c, defaults: defaults())
        let got = try habits(c)
        XCTAssertEqual(got.count, 3)
        for seed in s {
            guard let h = got.first(where: { $0.id == seed.id }) else { XCTFail("habit \(seed.name) missing"); continue }
            XCTAssertEqual(h.name, seed.name)
            XCTAssertEqual(h.createdAt, seed.created)
            XCTAssertEqual(h.currentStreak, seed.streak, "streak of \(seed.name)")
            XCTAssertEqual(h.isArchived, seed.archived)
            XCTAssertEqual(Set(h.checkIns.map(\.id)), Set(seed.checkIns.map(\.0)), "check-ins of \(seed.name)")
            for (cid, date, note) in seed.checkIns {
                let ci = h.checkIns.first { $0.id == cid }
                XCTAssertEqual(ci?.date, date)
                XCTAssertEqual(ci?.note, note)
                XCTAssertEqual(ci?.habit?.id, seed.id)
            }
        }
        XCTAssertEqual(try checkIns(c).count, 7)
    }

    func testSecondLaunchDoesNotDuplicate() throws {
        let c = try container()
        let cd = try coreData(seeds())
        let ud = defaults()
        try AppStartup.run(coreData: cd, container: c, defaults: ud)
        try AppStartup.run(coreData: cd, container: c, defaults: ud)
        XCTAssertEqual(try habits(c).count, 3)
        XCTAssertEqual(try checkIns(c).count, 7)
    }

    func testDoneFlagInUserDefaultsStopsRerun() throws {
        let cd = try coreData(seeds())
        let ud = defaults()
        let before = ud.dictionaryRepresentation()
        try AppStartup.run(coreData: cd, container: try container(), defaults: ud)
        let added = ud.dictionaryRepresentation().filter { before[$0.key] == nil }
        XCTAssertTrue(added.values.contains { ($0 as? Bool) == true || ($0 as? Int) == 1 }, "no done flag written: \(added.keys)")
        let fresh = try container()
        try AppStartup.run(coreData: cd, container: fresh, defaults: ud)
        XCTAssertEqual(try habits(fresh).count, 0, "migration ran again although the flag was set")
    }

    func testEmptyLegacyStoreIsMarkedDone() throws {
        let ud = defaults()
        let before = ud.dictionaryRepresentation()
        let c = try container()
        try AppStartup.run(coreData: try coreData([]), container: c, defaults: ud)
        XCTAssertEqual(try habits(c).count, 0)
        XCTAssertFalse(ud.dictionaryRepresentation().filter { before[$0.key] == nil }.isEmpty, "empty store not marked done")
    }
}
