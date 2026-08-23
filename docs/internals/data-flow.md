# Data Flow Traces

Three end-to-end walkthroughs. Each follows a real user action through every
file it touches. Use these when you need to know *exactly* where a request
goes.

## Trace 1: Anonymous user moves a slider in the playground

This is the most common path. Latency budget: < 16ms (one frame).

```
1. User drags the sparsity slider from 0% to 50%.
   File: apps/web/components/playground/config-panel.tsx
   Code: <input type="range" onChange={…}>
         calls setConfig({ ...config, sparsity: { …, ratio } })

2. State change in the parent.
   File: apps/web/app/playground/page.tsx
   Code: const [config, setConfig] = useState<CompressionConfig>(…)
         React schedules a re-render.

3. useMemo triggers: config changed.
   File: apps/web/app/playground/page.tsx
   Code: const estimate = useMemo(() => quickEstimate({ … }), [model, config, target])

4. Pure-function math runs.
   File: apps/web/lib/estimator.ts
   Code: quickEstimate(input) → {area_mm2, throughput, cost_per_chip, …}
   - effectiveParams() applies sparsity reduction
   - NODE_PARAMS lookup for the target
   - Murphy yield + NRE amortization for cost
   No network calls. No async. Returns synchronously.

5. The Pareto plot also recomputes: this useMemo iterates eight targets.
   File: apps/web/app/playground/page.tsx (paretoEstimates)

6. Three panels re-render with the new estimate.
   - apps/web/components/playground/results-panel.tsx (Metric cards)
   - apps/web/components/playground/floorplan.tsx (treemap)
   - apps/web/components/playground/pareto-plot.tsx (Recharts scatter)

7. React commits, browser paints.
```

**Total time:** sub-millisecond for the math, a few ms for React + Recharts.
The user sees instantaneous feedback. This is the entire reason the
client-side estimator exists.

## Trace 2: Authenticated user creates and compiles a project

Longer trace. Hits all four layers. The dashboard UI (`lib/api.ts`, the
projects pages) is not in the tree yet, so the frontend steps below are
marked *(planned)*; everything from the API inward is implemented.

### Phase A: Project creation

```
1. User clicks "Save as project" in the playground. (planned)
   File: apps/web/app/playground/page.tsx
   Code: api.createProject({name, model_source, compression, targets}, token)

2. Fetch wrapper sends the request. (planned)
   File: apps/web/lib/api.ts
   Code: request<Project>("/api/projects", {method: "POST", body, token})
   Headers: Authorization: Bearer <Clerk JWT>

3. FastAPI receives, dispatches to router.
   File: apps/api/app/main.py
   Mount: app.include_router(projects.router, prefix="/api/projects")

4. Auth dependency runs.
   File: apps/api/app/auth.py
   Function: get_current_user(credentials, x_dev_user_id)
   - In production: jwt.decode(token, CLERK_JWT_KEY, algorithms=["RS256"])
   - Returns CurrentUser(id, clerk_id, email)

5. Database session opened.
   File: apps/api/app/db.py
   Dependency: get_session() yields AsyncSession

6. Router handler runs.
   File: apps/api/app/routers/projects.py
   Function: create_project(body, session, current)
   - _ensure_user(session, current): upsert User row by clerk_id
   - Create Project ORM object with model_source/compression/targets as JSON
   - session.add(project), commit, refresh
   - Returns ProjectResponse (Pydantic auto-serializes)

7. Frontend receives Project, navigates to /projects/{id}.
```

### Phase B: Job submission

```
1. User clicks "Compile to RTL" on the project detail page. (planned)
   File: apps/web/app/projects/[id]/page.tsx
   Code: api.startCompress(id, token)

2. POST /api/projects/{id}/compress hits the API.
   File: apps/api/app/routers/projects.py
   Function: start_compress(project_id, session, current)

3. Authorization check.
   Helper: _load_project(session, project_id, current)
   - Verifies User owns the project. 404 otherwise.

4. Job creation + enqueue.
   Helper: _enqueue(session, project, job_type="compress")
   - Creates Job row with status="queued"
   - Sets project.status = "queued"
   - Commits BEFORE enqueueing; the worker must always find the row.
   - Calls enqueue_job(payload) where payload has model_source +
     compression_config + target_hardware as plain JSON.

5. Redis push.
   File: apps/api/app/queue.py
   Function: enqueue_job(job)
   Code: client.rpush("asicify:jobs", json.dumps(job))

6. API returns JobResponse to the frontend.
```

### Phase C: Worker pickup

```
1. Worker is blocked in BLPOP somewhere.
   File: apps/worker/worker/main.py
   Loop: popped = await client.blpop(["asicify:jobs"], timeout=30)

2. Job arrives, BLPOP returns. Dispatch.
   Function: dispatch(client, job)
   - Looks at job["job_type"]
   - For "compress" → calls run_compression_job(job, emit)
   - emit is a closure that publishes to asicify:progress:<project_id>

3. Compression pipeline runs.
   File: apps/worker/worker/pipeline/orchestrator.py
   Function: run_compression_job(job, emit)
   Stages run in order, each via _stage(emit, name, fn, *args):

   a. parse_model({id, type})
      File: apps/worker/worker/pipeline/parse.py
      Returns: ModelGraph (real module walk + HF attention detection)

   b. quantize_graph(graph, config)
      File: apps/worker/worker/pipeline/quantize.py
      Returns: ModelGraph with .quantization populated

   c. apply_sparsity(graph, config)
      File: apps/worker/worker/pipeline/sparsity.py
      Returns: ModelGraph with .sparsity_masks populated

   d. apply_decomposition(graph, config)
      File: apps/worker/worker/pipeline/decompose.py
      Returns: ModelGraph with .decompositions populated

   e. validate_quality(graph, config, baseline)
      File: apps/worker/worker/pipeline/validate.py
      Returns: dict with baseline / compressed / delta_pct

4. Each stage emits two events:
   - {"event": "stage_start", "stage": "<name>"}
   - {"event": "stage_complete", "stage": "<name>", "duration_ms": N, "metrics": {...}}

5. After all stages, the dispatcher emits:
   - {"event": "complete"}
```

### Phase D: Progress streaming back to the user

```
1. Frontend opened the WebSocket on page load. (planned)
   File: apps/web/lib/api.ts
   Function: subscribeProgress(projectId, onEvent)
   URL: ws://api/api/projects/{id}/progress

2. API accepts the WebSocket.
   File: apps/api/app/routers/progress.py
   Handler: progress_ws(websocket, project_id)
   Calls: subscribe_progress(project_id), an async generator

3. Generator subscribes to Redis pub/sub.
   File: apps/api/app/queue.py
   Function: subscribe_progress(project_id)
   - pubsub.subscribe(f"asicify:progress:{project_id}")
   - Yields each parsed message as a dict.

4. For each event, handler does ws.send_json(event).

5. Frontend's onEvent callback fires.
   - Updates UI to show stage_start/stage_complete cards.
   - On "complete": refetch project + artifacts.

6. WebSocket closes when the page unmounts.
```

The full journey: user click → REST → DB write → Redis push → BLPOP →
pipeline → Redis pub/sub → WebSocket → React state. Every step is observable
either via the database or Redis-CLI.

## Trace 3: Worker generates the RTL package

This trace focuses on what happens during a `generate-rtl` job, drilling
into the codegen specifically.

```
1. Job dispatched.
   File: apps/worker/worker/main.py
   Calls: run_rtl_job(job, emit)

2. Parse model + config.
   File: apps/worker/worker/rtl/generator.py
   Function: run_rtl_job
   - graph = parse_model(job["model_source"])
   - config = _cfg_from_dict(job["compression_config"])
   - emit({"event": "stage_start", "stage": "rtl_generation"})

3. Render the package.
   Function: render_package(graph, config) → bytes
   - Picks multiplier strategy from config.quantization
   - Loads each Jinja2 template via env.get_template(name).render(...)

4. Per-template rendering, in order:

   a. top.v.j2 → top.v
      Wires inputs → layer_0 → layer_1 → … → outputs.
      Each layer instance is named u_<index>.

   b. weights.vh.j2 → weights.vh
      One localparam per linear layer, plus embedding tables and the
      softmax LUT.

   c. For each layer with kind in (linear, attention, layernorm, embedding):
      - linear_layer.v.j2 (or fp16_layer.v.j2) / attention_block.v.j2 /
        layernorm.v.j2 / embedding.v.j2
        → modules/layer_<sym>.v (attention_<sym>.v for attention)
      - Includes weights.vh

   d. softmax.v.j2 → softmax.v, kv_cache.v.j2 → kv_cache.v
      Shared submodules, always emitted.

   e. tb_top.py.j2 → tb_top.py
      Cocotb testbench that imports reference.py.

   f. reference.py.j2 → reference.py
      Bit-exact NumPy reference implementation.

   g. Makefile.j2 → Makefile
      sim / synth-yosys / synth-vivado targets.

   h. yosys.tcl.j2 → synthesis/yosys.tcl
      ECP5 synthesis script.

   i. nextpnr.sh.j2 → synthesis/nextpnr.sh
      ECP5 place-and-route + bitstream pack.

   j. vivado.tcl.j2 → synthesis/vivado.tcl
      Xilinx synthesis + P&R.

   k. README.md.j2 → README.md
      User-facing package README.

5. Pack into a zip in memory.
   Code: ZipFile(buf, "w", ZIP_DEFLATED); one writestr per file.
   Returns: bytes

6. Upload to R2.
   (Currently stubbed; TODO: r2_client.put_object(Bucket=…, Key=…))

7. Create Artifact row.
   (Currently stubbed; TODO: insert via internal API call from worker.)

8. Emit completion.
   emit({"event": "stage_complete", "stage": "rtl_generation", "metrics": {...}})
```

The output zip structure:

```
<model>.zip
├── README.md
├── top.v
├── weights.vh
├── softmax.v
├── kv_cache.v
├── modules/
│   ├── layer_embed.v
│   ├── attention_block_0_attn.v
│   ├── layer_block_0_ffn.v
│   ├── layer_block_0_ln.v
│   └── …
├── tb_top.py
├── reference.py
├── Makefile
└── synthesis/
    ├── yosys.tcl
    ├── nextpnr.sh
    └── vivado.tcl
```

The user can `unzip` and immediately `make sim` (cocotb + Verilator) or
`make synth-yosys` (open-source ECP5 flow).

## Where things can go wrong

A short list of failure modes and where they surface:

| Symptom                                  | Likely cause                                  | Where to look                                    |
| ---------------------------------------- | --------------------------------------------- | ------------------------------------------------ |
| Playground feels laggy                   | Pareto plot iterating too many targets        | apps/web/app/playground/page.tsx (paretoEstimates) |
| `quickEstimate` returns NaN              | Bad cell library entry                        | apps/web/lib/estimator.ts (NODE_PARAMS)          |
| API 401 in dev                           | CLERK_JWT_KEY set but no token, or vice versa | apps/api/app/auth.py                             |
| Job stays "queued" forever               | Worker not running or wrong REDIS_URL         | apps/worker/worker/main.py                       |
| WebSocket disconnects after a few events | Redis pub/sub timeout, network                | apps/api/app/queue.py (subscribe_progress)       |
| Generated Verilog doesn't lint           | Template typo, undefined variable             | StrictUndefined raises in apps/worker/worker/rtl/generator.py |
| Artifact download 403                    | R2 credentials, or presigned URL expired      | apps/api/app/storage.py                          |
| Playground numbers diverge from worker   | Sync drift between TS and Python estimators   | Compare estimator.ts:NODE_PARAMS vs targets.py:ASIC_NODES |

## Useful debugging hooks

- `redis-cli -u $REDIS_URL LRANGE asicify:jobs 0 -1`: see queued jobs
- `redis-cli -u $REDIS_URL SUBSCRIBE 'asicify:progress:*'`: tail all progress
- `psql $DATABASE_URL -c "select id, status, updated_at from projects order by updated_at desc limit 10"`: recent projects
- `mc ls minio/asicify-artifacts` (with mc configured): list R2/MinIO bucket
- API has `/docs`, the full OpenAPI explorer in dev

When you're trying to reproduce a bug, start at the layer boundary closest
to the symptom. UI bug → playground state. Job bug → Redis. Compute bug →
worker logs. The layer split is what makes this tractable.
