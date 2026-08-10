# Conference demo script

Target length: 3–5 minutes.

## Before the talk

```bash
uv sync --locked --all-groups
cp .env.example .env
az login
./scripts/check.sh
```

Start the demo once before going on stage so Azure authentication and package
caches are warm.

Keep a terminal recording as fallback.

## Live sequence

### 1. Show that the services are independent

```bash
./scripts/demo.sh cards
```

Point out:

- different processes and ports;
- same A2A skill contract;
- different framework tags;
- A2A v1 JSON-RPC interface.

### 2. Show the controlled comparison

```bash
./scripts/demo.sh compare
```

Explain that model, prompt headings, domain tools, and user input are held
constant. The code comparison is about runtime design, not answer quality from
different models.

### 3. Run cross-framework collaboration

```bash
./scripts/demo.sh collaborate
```

Narration:

1. MAF performs the initial enterprise review.
2. Only the public A2A artifact crosses the boundary.
3. LangGraph maps A2A `context_id` to its `thread_id` and challenges the review.
4. The critique returns to the original MAF A2A session.
5. MAF produces the final synthesis.

### 4. End on the boundary

Use this line:

> MAF does not execute the LangGraph graph. It composes a remote agent it does
> not own through a common Agent contract.

Then show:

```text
A2A context is shared correlation.
It is not shared memory, shared checkpointing, or shared trust.
```

## Optional inventory composition demo

Target length: 3 minutes.

Use deterministic mode for a conference rehearsal:

```dotenv
INVENTORY_MODE=fixture
```

Then run:

```bash
./scripts/demo.sh inventory --product 火雞肉飯 --quantity 20
```

Narration:

1. The local MAF orchestrator receives an order request.
2. Its Foundry model selects `check_inventory_via_a2a`.
3. That function tool is an actual remote `A2AAgent`, not a direct inventory
   HTTP wrapper.
4. The LangGraph service parses strict JSON and calls the inventory gateway
   exactly once.
5. A visible conditional edge selects `sufficient`, `insufficient`, or
   `manual_review`.
6. The A2A artifact returns to MAF, which applies the enterprise caveats.

Use this line:

> MAF owns delegation; LangGraph owns deterministic decision control; A2A owns
> the service boundary.

For the live endpoint:

```dotenv
INVENTORY_MODE=live
INVENTORY_FALLBACK_TO_FIXTURE=true
```

The live quantity is intentionally variable. If a live failure triggers
`fixture-fallback`, the graph always returns `manual_review`; do not hide that
branch during the presentation.

## If Microsoft Foundry is unavailable

Run:

```bash
./scripts/check.sh
```

The test suite performs real in-process A2A JSON-RPC round trips with
deterministic fake models, so the source-level protocol proof remains
demonstrable without a live model call.
