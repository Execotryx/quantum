# D4 extraction repair plan

The [OpenSpec change](../openspec/changes/repair-d4-extraction-poles/)
records the source review and Astra's predictions for the four failing
shots. It separates the existing cloud evidence at converter entry from
the native extraction check still required to locate the initial divergence.
The plan tests a homogeneous routing ablation and then addresses the
repeated-node local pole across extraction and synthesis. It uses matched
historical inputs for regression and separately registered cloud draws for
full verifier results and pricing.

`openspec validate repair-d4-extraction-poles --strict` passed.
