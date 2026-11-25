# Q880 decoder regeneration

Both isolated Ubuntu builds reproduced the published D5 Q880
circuit. The circuit hash is
`e8083195cec294f2adde9f1b991bcc348233f549a49e5083ac25a12d0777385b`.
It uses 880 qubits and 906,693 static Toffoli-like gates. The KMB is
722,541,720 bytes.

The build adapter checks the source manifest and official backend before
running the upstream entry point. The upstream documented CPython
3.13.17 build was unavailable from uv. Both local builds used CPython
3.13.15 with the upstream NumPy 2.5.4 pin and reproduced the published
bytes. The adapter runs took 138.33 and 119.42 seconds. The maximum
resident set sizes reported by GNU time were 1,535,836 and 1,536,076 KiB.

Full verifier results and pooled pricing are pending selection of the
registered candidate field.

[Regeneration receipts](evidence/vendored-dqi/d5-regeneration/) ·
[Source manifest](../third_party/dqi-d5/SOURCE.json)
