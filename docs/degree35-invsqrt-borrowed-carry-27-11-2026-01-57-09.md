# Source-borrowing carry for rounded inverse square root

The ripple stores low carries in the current operand and restores it
after each addition. The forward majority network computes the
carry independently of the multiplier bit. The reverse network
restores the operand and uses the multiplier bit to gate the sum.
An unequal-width add applies an increment to the remaining high
target. One variant uses the native incrementer. The other borrows an
input word, adds that word with carry-in, and subtracts the same word
with zero carry. The active multiplier control stays outside that
borrowed word.
[Ripple-carry construction](https://arxiv.org/abs/quant-ph/0410184)

| Correction layout, including both products and cleanup | Qubits | Executed Toffolis | Width times gates |
| --- | ---: | ---: | ---: |
| Native controlled rows | 107 | 2,856 | 305,592 |
| Native adder with measured partial products | 129 | 2,190 | 282,510 |
| Borrowed carry with controlled rows | 103 | 2,660 | 273,980 |
| Borrowed carry with measured partial products | 125 | 2,608 | 326,000 |
| Dirty upper increment with controlled rows | 86 | 3,942 | 339,012 |
| Dirty upper increment with measured partial products | 108 | 3,890 | 420,120 |

The 12 retained control binaries rebuilt byte-for-byte. The new
serialized forward and reverse slices passed the same **1,536
fixtures per case**, including all 192 intervals. The checks covered
both signed products, all source registers, the borrowed input, clean
scratch, and zero residual phase. The one-guard model reproduced its
full-domain result at **81.60%** worst tolerance use. The E-backed
Ubuntu regression suite passed **155 tests**, including exhaustive
small-width addition and subtraction with arbitrary dirty inputs.
Pyright and strict OpenSpec validation passed.
[Registered comparison](evidence/aggregate36-20261126/invsqrt-borrowed-carry-registration.json)
· [Phase screen](evidence/aggregate36-20261126/invsqrt-borrowed-carry-screen.json)
· [Native receipts](evidence/aggregate36-20261126/invsqrt-borrowed-carry-native.json)

The minimum declared width was **86 qubits**. The lowest measured
cost product was **273,980**, a **3.02%** reduction from **282,510**.
The remaining gap to **52,119.68** excludes these schedules before
coefficient loading, normalization, and rotations. The best
complete cloud score remains **33.20483975**.
[Budget and prior arithmetic comparison](degree35-invsqrt-rounded-products-27-11-2026-01-47-52.md)
