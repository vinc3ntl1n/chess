# M1 — Part 1: Engine Skeleton + Bitboard Basics

**Estimated time:** 2–4 hours
**Prerequisites:** C++ basics (classes, headers, `enum class`, basic templates), CMake basics, command-line comfort
**Where this fits:** This is sub-step 1.1 of milestone M1 in the project brief. You'll build the foundation that every other piece of the engine sits on.

---

## Learning goals

By the end of this part you will:

1. Understand why bitboards are the standard board representation in serious chess engines.
2. Be fluent with the LERF (Little-Endian Rank-File) square indexing convention.
3. Be able to set, clear, test, count, and iterate over bits in a `uint64_t` using C++20's `<bit>` header.
4. Have a working CMake project that compiles with strict warnings and runs unit tests via `doctest`.

You are NOT trying to write a chess engine in this part — just the substrate.

---

## What you're building

A new `engine/` directory inside the repo with this layout:

```
engine/
├── CMakeLists.txt
├── third_party/
│   └── doctest.h           # download from doctest's GitHub
├── src/
│   ├── types.hpp           # Color, PieceType, Square, Move + helpers
│   ├── bitboard.hpp        # Bitboard typedef + bit ops (header-only)
│   └── main.cpp            # stub that prints "engine alive"
└── tests/
    └── test_bitboard.cpp   # doctest unit tests
```

When you're done, two binaries live in `engine/build/`:

- `./engine` → prints `engine alive`
- `./tests` → runs all your bitboard tests, reports pass/fail

Both compile with `-Wall -Wextra -Wpedantic` with **zero warnings**.

---

## Part A — `engine/src/types.hpp`

This file defines the basic vocabulary for the rest of the engine. Everything is `#pragma once` and lives in a namespace (suggest `chess::` or just no namespace at all — your call, but be consistent).

### A.1 — `enum class Color`

Two values: `WHITE` and `BLACK`. Underlying type doesn't really matter; default `int` is fine.

Add a free function `Color other(Color c)` that returns the opposite color. (Or overload `operator~` if you want a fancier API. Either is fine; just pick one.)

### A.2 — `enum class PieceType`

Six values: `PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING`. Make the underlying values `0..5` explicit (e.g. `PAWN = 0`) — you'll be using them to index arrays of bitboards.

Optionally add a `NONE` sentinel at the end. Many engines find it useful when, e.g., `piece_at(sq)` needs to say "nothing here." If you add it, give it value `6` so it's still array-friendly.

### A.3 — `Square` type

```cpp
using Square = int;
```

Why `int` and not `uint8_t`? Because you'll do arithmetic like `sq + 8` or comparisons against `-1` sentinels, and unsigned underflow will silently bite you. Memory is not a concern here.

Add these free functions (all `constexpr inline`):

| Signature | Behavior |
|---|---|
| `int file_of(Square sq)` | returns 0..7 (a..h) |
| `int rank_of(Square sq)` | returns 0..7 (rank 1..rank 8) |
| `Square make_square(int file, int rank)` | inverse of the above |
| `std::string square_name(Square sq)` | returns e.g. `"e4"` |

Add square name constants. Easiest: a plain `enum` (not `enum class`) so the names act like `int` constants:

```cpp
enum : int {
    A1 = 0, B1, C1, D1, E1, F1, G1, H1,
    A2,     B2, ..., H2,
    ...
    A8, B8, C8, D8, E8, F8, G8, H8 = 63
};
```

These let you write `make_move(E2, E4)` in tests instead of `make_move(12, 28)`.

### A.4 — `Move` type

A `Move` is packed into a single `uint16_t`:

```
bits 0–5  : from square (0..63)
bits 6–11 : to square   (0..63)
bits 12–15: flags       (0..15)
```

Define:

```cpp
using Move = uint16_t;
```

Then `constexpr inline` accessors:

| Signature | Behavior |
|---|---|
| `Move make_move(Square from, Square to, int flags = 0)` | pack |
| `Square from_sq(Move m)` | unpack `m & 0x3F` |
| `Square to_sq(Move m)` | unpack `(m >> 6) & 0x3F` |
| `int flags_of(Move m)` | unpack `(m >> 12) & 0xF` |

For now, give yourself an `enum class MoveFlag : int` with these 14 values:

```
QUIET = 0, DOUBLE_PAWN = 1,
KING_CASTLE = 2, QUEEN_CASTLE = 3,
CAPTURE = 4, EP_CAPTURE = 5,
PROMO_N = 8, PROMO_B = 9, PROMO_R = 10, PROMO_Q = 11,
PROMO_N_CAPTURE = 12, PROMO_B_CAPTURE = 13, PROMO_R_CAPTURE = 14, PROMO_Q_CAPTURE = 15,
```

You won't *use* most of these until movegen (Part 3). Defining them now keeps `make_move` honest and the test cases clean.

---

## Part B — `engine/src/bitboard.hpp`

Header-only. `#pragma once`. Include `<cstdint>` and `<bit>`.

### B.1 — The typedef

```cpp
using Bitboard = uint64_t;
```

That's literally it for the type. The rest is functions.

### B.2 — Bit operations

All `constexpr inline`. All take `Bitboard` and `Square`:

| Function | Definition |
|---|---|
| `set_bit(Bitboard& bb, Square sq)` | `bb \|= (1ULL << sq);` |
| `clear_bit(Bitboard& bb, Square sq)` | `bb &= ~(1ULL << sq);` |
| `test_bit(Bitboard bb, Square sq)` | `(bb >> sq) & 1ULL` |

**Pitfall #1:** `1ULL`, not `1`. Plain `1` is `int`, and shifting an `int` by ≥32 is undefined behavior. Every C++ chess tutorial mentions this and people still get bit by it.

### B.3 — Population count and LSB

| Function | Definition |
|---|---|
| `popcount(Bitboard bb)` | wrap `std::popcount(bb)` — number of set bits |
| `lsb(Bitboard bb)` | wrap `std::countr_zero(bb)` — index of lowest set bit |
| `pop_lsb(Bitboard& bb)` | computes `lsb(bb)`, then `bb &= (bb - 1)` to clear it, returns the index |

**Pitfall #2:** `lsb(0)` and `pop_lsb(0)` are undefined. Document this. Callers must check `bb != 0` first. You'll always be calling these inside a `while (bb) { ... }` loop so this isn't a real issue in practice — but assert it in debug if you want to be paranoid.

**Pitfall #3:** the trick `bb & (bb - 1)` clears the lowest set bit. It's worth understanding *why*: subtracting 1 flips the trailing zeros to ones and the lowest set bit to a zero; AND'ing with the original wipes everything below the original lowest set bit and unsets it. This is the same operation as `bb ^ (1ULL << lsb(bb))` but faster on most hardware.

### B.4 — A debug helper (optional but recommended)

```cpp
std::string bb_to_string(Bitboard bb);
```

Returns an 8x8 ASCII grid (rank 8 on top, rank 1 on bottom, `.` for empty, `1` for set). Two minutes to write and saves you hours when movegen breaks. Mark it `inline` since the header is header-only.

---

## Part C — `engine/src/main.cpp`

Just a stub to prove linkage works:

```cpp
#include <iostream>

int main() {
    std::cout << "engine alive\n";
    return 0;
}
```

You can include `bitboard.hpp` and print `popcount(0xFFULL)` if you want, but it's not required.

---

## Part D — Build system: `engine/CMakeLists.txt`

Top-level CMake config. Things it must do:

1. `cmake_minimum_required(VERSION 3.20)`
2. `project(chess_engine CXX)`
3. Set `CMAKE_CXX_STANDARD 20`, `CMAKE_CXX_STANDARD_REQUIRED ON`, `CMAKE_CXX_EXTENSIONS OFF`
4. Add a target `engine` from `src/main.cpp`
5. Add a target `tests` from `tests/test_bitboard.cpp`
6. Both targets get `target_include_directories(... PRIVATE src third_party)` so they can `#include "bitboard.hpp"` and `#include "doctest.h"`
7. Both targets get compile flags `-Wall -Wextra -Wpedantic` (and treat warnings as errors with `-Werror` if you're feeling principled)

You do NOT need `add_library` for shared code — the headers are header-only, so each target just includes them directly.

---

## Part E — Testing: `engine/third_party/doctest.h` + `engine/tests/test_bitboard.cpp`

### E.1 — Get doctest

doctest is a single header file. Download `doctest.h` from <https://github.com/doctest/doctest/blob/master/doctest/doctest.h> (raw view) and save to `engine/third_party/doctest.h`. That's the entire dependency.

### E.2 — Write the test file

Top of file:

```cpp
#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include "doctest.h"
#include "bitboard.hpp"
#include "types.hpp"
```

Then write **at least these test cases**:

1. `set_bit` on an empty bitboard with `E4` produces `1ULL << 28`.
2. `clear_bit` on a board with only `E4` set produces 0.
3. `test_bit` returns true for the squares you set, false otherwise.
4. `popcount` of `0` is 0; of `0xFFULL` is 8; of `~0ULL` is 64.
5. `lsb` of `1ULL << 17` is 17.
6. `pop_lsb` on a bitboard with bits {3, 17, 42} set: three calls return 3, 17, 42 in that order, and the bitboard is 0 afterward.
7. `file_of(E4)` is 4, `rank_of(E4)` is 3, `make_square(4, 3)` is `E4`, `square_name(E4)` is `"e4"`.
8. Round-trip: `from_sq(make_move(E2, E4)) == E2` and `to_sq(make_move(E2, E4)) == E4`.

doctest test syntax:

```cpp
TEST_CASE("set_bit sets the right bit") {
    Bitboard bb = 0;
    set_bit(bb, E4);
    CHECK(bb == (1ULL << 28));
}
```

`CHECK` continues on failure; `REQUIRE` aborts the test case on failure. Use `CHECK` unless a later assertion would crash on the failure of the earlier one.

---

## Verification (acceptance criteria)

You're done with Part 1 when:

- [ ] `engine/` directory exists with the structure above
- [ ] `cd engine && mkdir build && cd build && cmake .. && make` produces both `engine` and `tests` binaries
- [ ] Compilation produces ZERO warnings with `-Wall -Wextra -Wpedantic`
- [ ] `./engine` prints `engine alive`
- [ ] `./tests` reports all test cases passing
- [ ] You can explain (out loud or in writing) why `bb & (bb - 1)` clears the lowest set bit

---

## Common pitfalls (in priority order)

1. **`1` instead of `1ULL`.** Shifting an `int` by ≥32 is undefined behavior. If your tests on high squares (rank 5+) silently fail, this is almost always the cause.
2. **Forgetting `inline` / `constexpr` on header-defined functions.** If you get linker errors saying "multiple definition of `set_bit`", you have non-inline functions defined in a header included in two TUs.
3. **`#include "bitboard.hpp"` order.** doctest's `IMPLEMENT_WITH_MAIN` macro defines `main()`. Make sure your test file is the only one with that macro.
4. **CMake remembers things you wish it wouldn't.** If you change something fundamental (compiler flags, C++ standard) and weird errors appear, `rm -rf build/` and start fresh.
5. **`pop_lsb` mutating its argument.** Make sure your signature is `Bitboard&`, not `Bitboard`. If you take by value, the caller's bitboard never gets cleared and your `while (bb)` loops are infinite.

---

## Hints (read if stuck)

- The cleanest way to write `square_name` is `{char('a' + file_of(sq)), char('1' + rank_of(sq)), '\0'}` then return as `std::string`.
- For `bb_to_string`, iterate ranks 7 down to 0, and within each rank iterate files 0 to 7, and check `test_bit(bb, make_square(file, rank))`.
- doctest uses `CHECK_EQ`, `CHECK_NE`, etc. for explicit equality; plain `CHECK(a == b)` works too and gives slightly nicer error messages with stringification.
- If you don't have CMake installed: `brew install cmake`. If you don't have a recent enough clang for `<bit>` (need C++20): the Apple LLVM that ships with Xcode 14+ is fine; otherwise `brew install llvm`.

---

## When you're done

Tell me "Part 1 done" and I'll review the code. Then we move to Part 2: board representation + FEN parsing.
