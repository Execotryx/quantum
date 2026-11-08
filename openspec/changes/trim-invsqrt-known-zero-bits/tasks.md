## 1. Development proof and freeze

- [x] 1.1 Verify table high bits, control trace and pre-emission resource model.
- [x] 1.2 Check all domain inputs, intermediate subtraction bounds and output bit.
- [x] 1.3 Emit the candidate, run native phase/cleanup fixtures and reject high-bit mutations.
- [x] 1.4 Rebuild independently twice and record frozen hashes and receipts.

## 2. Preregistered verification

- [x] 2.1 Register the candidate, clean source, control, contract and exact gates.
- [x] 2.2 Pass the complete official trajectory verifier on the registered KMB.
- [x] 2.3 Pass a fresh, one-use confirmation on identical bytes.
- [ ] 2.4 Run the paired extracted-archive metric and reconcile retained members and costs.
- [ ] 2.5 Record final receipts and promotion decision without overwriting prior evidence.
