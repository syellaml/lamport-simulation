"""
Simulasi Lamport Logical Clock - 3 Proses (P1, P2, P3)

Aturan Lamport:
  R1. Event lokal : L = L + 1
  R2. Send        : L = L + 1, lalu kirim (pesan membawa L)
  R3. Receive     : L = max(L_lokal, L_pesan) + 1
"""
from itertools import product


class Event:
    def __init__(self, eid, proc, kind, ts, desc, msg=None):
        self.eid = eid        # id unik, mis. "P1.2"
        self.proc = proc
        self.kind = kind      # local / send / recv
        self.ts = ts
        self.desc = desc
        self.msg = msg        # nama pesan (untuk send/recv)


class Process:
    def __init__(self, name, log):
        self.name = name
        self.clock = 0
        self.count = 0
        self.log = log

    def _record(self, kind, desc, msg=None):
        self.count += 1
        ev = Event(f"{self.name}.{self.count}", self.name, kind,
                   self.clock, desc, msg)
        self.log.append(ev)
        return ev

    def local(self, desc):
        self.clock += 1                                  # R1
        return self._record("local", desc)

    def send(self, msg, dest):
        self.clock += 1                                  # R2
        self._record("send", f"kirim {msg} -> {dest}", msg)
        return {"name": msg, "ts": self.clock, "src": self.name}

    def receive(self, message):
        old = self.clock
        self.clock = max(self.clock, message["ts"]) + 1  # R3
        ev = self._record(
            "recv",
            f"terima {message['name']} dari {message['src']} "
            f"(max({old},{message['ts']})+1)", message["name"])
        return ev


def run_scenario():
    log = []
    P1, P2, P3 = (Process(n, log) for n in ("P1", "P2", "P3"))

    # P2 memulai: satu event lokal, lalu menyebar dua pesan
    P2.local("inisialisasi")
    m1 = P2.send("m1", "P1")
    m2 = P2.send("m2", "P3")

    # P1 menerima m1, bekerja, lalu meneruskan ke P3
    P1.receive(m1)
    P1.local("olah data")
    m3 = P1.send("m3", "P3")

    # P3 bekerja sendiri dulu, baru menerima dua pesan
    P3.local("cek sensor")
    P3.receive(m2)
    P3.receive(m3)
    m4 = P3.send("m4", "P2")

    # P1 dan P2 bekerja lagi tanpa saling berkomunikasi (concurrent)
    P1.local("tulis log")
    P2.local("cek antrean")
    P2.receive(m4)

    # P1 mengirim laporan terakhir ke P2
    m5 = P1.send("m5", "P2")
    P2.receive(m5)
    return log


# ---------- Happened-before (dihitung independen dari timestamp) ----------
def happened_before(log):
    ids = [e.eid for e in log]
    hb = {(a, b): False for a, b in product(ids, ids)}

    # 1) urutan dalam satu proses
    by_proc = {}
    for e in log:
        by_proc.setdefault(e.proc, []).append(e)
    for evs in by_proc.values():
        for i in range(len(evs)):
            for j in range(i + 1, len(evs)):
                hb[(evs[i].eid, evs[j].eid)] = True

    # 2) send -> receive untuk pesan yang sama
    sends = {e.msg: e for e in log if e.kind == "send"}
    for e in log:
        if e.kind == "recv":
            hb[(sends[e.msg].eid, e.eid)] = True

    # 3) transitive closure (Floyd-Warshall)
    for k in ids:
        for i in ids:
            if hb[(i, k)]:
                for j in ids:
                    if hb[(k, j)]:
                        hb[(i, j)] = True
    return hb


def main():
    log = run_scenario()

    print("=" * 78)
    print("TABEL EVENT & LAMPORT TIMESTAMP")
    print("=" * 78)
    print(f"{'Event':<7}{'Proses':<8}{'Tipe':<7}{'L':<4}Keterangan")
    print("-" * 78)
    for e in log:
        print(f"{e.eid:<7}{e.proc:<8}{e.kind:<7}{e.ts:<4}{e.desc}")

    hb = happened_before(log)
    ev = {e.eid: e for e in log}
    ids = [e.eid for e in log]

    # ---- Verifikasi 1: Clock Condition  (a -> b  =>  L(a) < L(b)) ----
    print("\n" + "=" * 78)
    print("VERIFIKASI 1: Clock Condition  (a -> b  =>  L(a) < L(b))")
    print("=" * 78)
    pairs = [(a, b) for a, b in product(ids, ids) if hb[(a, b)]]
    violations = [(a, b) for a, b in pairs if not ev[a].ts < ev[b].ts]
    print(f"Pasangan kausal diperiksa : {len(pairs)}")
    print(f"Pelanggaran               : {len(violations)}")
    print("HASIL:", "LULUS" if not violations else f"GAGAL {violations}")

    # ---- Verifikasi 2: konkuren ----
    print("\n" + "=" * 78)
    print("VERIFIKASI 2: Event konkuren (tidak ada hubungan kausal)")
    print("=" * 78)
    print("Catatan: L(a) < L(b) TIDAK berarti a -> b (converse tidak berlaku).")
    concurrent = [(a, b) for a, b in product(ids, ids)
                  if a < b and not hb[(a, b)] and not hb[(b, a)]]
    false_implication = 0
    for a, b in concurrent:
        la, lb = ev[a].ts, ev[b].ts
        note = ""
        if la != lb:
            false_implication += 1
            note = "<- timestamp berbeda, tapi TIDAK ada kausalitas"
        print(f"  {a:<5}|| {b:<5} L={la} vs L={lb} {note}")
    print(f"Total pasangan konkuren: {len(concurrent)}")

    # ---- Verifikasi 3: total ordering ----
    print("\n" + "=" * 78)
    print("VERIFIKASI 3: Total Ordering (sort by (L, process_id))")
    print("=" * 78)
    total = sorted(log, key=lambda e: (e.ts, e.proc))
    for i, e in enumerate(total, 1):
        print(f"  {i:>2}. {e.eid:<5} (L={e.ts}, {e.proc})  {e.desc}")

    pos = {e.eid: i for i, e in enumerate(total)}
    consistent = all(pos[a] < pos[b] for a, b in pairs)
    print("\nTotal order konsisten dengan causal order:",
          "YA" if consistent else "TIDAK")


if __name__ == "__main__":
    main()
