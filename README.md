# StepStep Support Agent

AI-powered customer support agent prototype for a footwear retailer.

The system answers customer questions using a local knowledge base, retrieves customer-scoped order information, evaluates supported business rules deterministically, and escalates requests when the available information is insufficient to act safely.

The prototype is intentionally small. The focus is on AI engineering judgment, control boundaries, failure handling, testing, observability, and safe behavior rather than infrastructure scale.

---

## What it does

The support agent can:

- Answer questions using a knowledge base
- Retrieve orders using both `order_id` and `customer_id`
- Evaluate cancellation eligibility using deterministic business rules
- Prevent cross-customer order disclosure
- Refuse to infer unsupported business workflows
- Escalate unresolved requests to human support
- Detect and contain repeated tool calls
- Enforce a maximum agent iteration limit
- Produce structured JSON observability events
- Expose the agent through a FastAPI API

The prototype does **not** perform destructive order mutations such as actually cancelling an order.

---

## Architecture

```text
                          ┌──────────────────┐
                          │     FastAPI      │
                          │   /api/v1/chat   │
                          └────────┬─────────┘
                                   │
                              AgentContext
                              request_id
                              customer_id
                                   │
                          ┌────────▼─────────┐
                          │  SupportAgent    │
                          │                  │
                          │  Groq LLM       │
                          │  Tool loop       │
                          │  Guardrails      │
                          └────────┬─────────┘
                                   │
                 ┌─────────────────┼────────────────────┐
                 │                 │                    │
                 ▼                 ▼                    ▼
          Knowledge Tool      Order Tool          Policy Tool
                 │                 │                    │
                 ▼                 ▼                    ▼
          Embedding Search     Repository         Domain Rules
                 │                 │                    │
                 ▼                 ▼                    │
          Similarity Threshold  Customer Scope          │
                                   │                    │
                                   └──────────┬─────────┘
                                              │
                                              ▼
                                       Escalation Tool
```

### Responsibility boundaries

The LLM is responsible for:

- Understanding the customer's request
- Selecting available tools
- Interpreting structured tool results
- Producing the final conversational response

Application code remains responsible for:

- Customer authorization boundaries
- Business rules
- Knowledge retrieval thresholds
- Tool availability
- Action boundaries
- Escalation
- Agent iteration limits

The model is therefore not treated as the authority for security or business-critical decisions.

---

## Knowledge retrieval

The prototype uses semantic retrieval rather than keyword matching.

### Embedding model

```text
sentence-transformers/all-MiniLM-L6-v2
```

Embeddings are generated locally and compared using normalized vector similarity.

The knowledge corpus is intentionally small, so the prototype uses an in-memory index rather than introducing a managed vector database.

### Retrieval threshold

A minimum cosine-similarity threshold of `0.50` is applied.

Results below the threshold are not returned to the agent.

This was introduced after observing that an unsupported request could retrieve a semantically related policy with a score of `0.4171`.

Example evaluation:

| Query                                              | Highest score | Result      |
| -------------------------------------------------- | ------------: | ----------- |
| How long does standard shipping take?              |        0.6780 | Relevant    |
| What is the return policy?                         |        0.5654 | Relevant    |
| Can I cancel my order?                             |        0.6304 | Relevant    |
| Can I change the color of my shoes after delivery? |        0.4171 | Unsupported |
| What is the weather in Singapore today?            |        0.0607 | Unsupported |
| Can you tell me a joke?                            |        0.0735 | Unsupported |

The threshold is a prototype heuristic, not a universal semantic boundary. A production system should calibrate it using a larger labeled evaluation dataset.

---

## Customer-scoped order access

Order retrieval requires both:

```text
order_id
customer_id
```

For example:

```python
get_order(order_id, customer_id)
```

Knowing an order ID alone is not sufficient to retrieve the order.

An order belonging to another customer is treated externally the same way as an unknown order:

```text
Order not found
```

This prevents the system from revealing whether another customer's order exists.

The customer ID supplied to the API represents the authenticated customer context for this prototype.

> Important: a client-provided customer ID is not a real authentication mechanism. In production, the customer identity must be derived from a verified authentication token or session.

---

## Deterministic business rules

Business-critical decisions are implemented outside the LLM.

For example, cancellation eligibility is determined by application logic:

```text
processing → eligible

shipped   → not eligible

delivered → not eligible

cancelled → not eligible
```

The LLM can request cancellation evaluation, but it cannot override the deterministic result.

The prototype also does not expose an order mutation tool.

Therefore the agent must not claim:

> "Your order has been cancelled."

unless an application tool actually performs and confirms that operation.

This boundary was introduced after an early agent test generated a response implying that a cancellation would be performed even though no cancellation operation existed.

---

## Escalation

When the knowledge base cannot safely resolve a request, the agent should not construct a plausible workflow from related information.

Instead, it can escalate the request using:

```text
escalate_to_support
```

### Example

Customer:

```text
I want to exchange ORD-1001 for a different size.
```

The knowledge base does not contain an exchange policy.

The resulting flow is:

```text
search_knowledge
        ↓
no sufficiently relevant policy
        ↓
escalate_to_support
        ↓
final response
```

This behavior was added after an earlier failure where the model repeatedly searched the knowledge base and eventually inferred an unsupported exchange workflow from the returns policy.

The defect and corrective actions are documented in `DECISION_LOG.md`.

---

## Out-of-domain handling

The agent is intentionally scoped to StepStep customer-support requests.

Requests outside that domain should not be answered using general model knowledge, and they should not be routed into StepStep business workflows simply because the request mentions StepStep.

During evaluation, an unrelated request such as:

> Can you recommend a laptop for software development?

was initially treated as a support-related knowledge request.

A similar failure occurred when an unrelated request mentioned StepStep, showing that entity mentions alone were insufficient to establish domain relevance.

The system prompt was strengthened to explicitly define the supported domain and prohibit business-tool use for unrelated requests.

The out-of-domain evaluation suite now covers unrelated requests across several categories and verifies that the agent does not invoke StepStep business tools for those requests.

This is intentionally handled through the existing agent boundary rather than adding a separate classifier or another LLM call. The domain is small enough that introducing another routing component would add complexity without sufficient evidence that it was necessary.

---

## Agent safety controls

The agent includes several application-level controls:

### Tool iteration limit

The agent has a maximum number of tool iterations.

If the limit is reached, the request fails safely rather than continuing indefinitely.

### Repeated tool-call protection

The application tracks tool calls and prevents the agent from repeatedly issuing the same tool request without making progress.

### Structured tool responses

Tools return explicit Pydantic models rather than arbitrary strings.

This makes tool behavior predictable and easier to test.

### No unrestricted capabilities

The LLM has access only to explicitly defined application tools.

It does not have:

- Arbitrary web access
- Code execution
- Database access
- Unrestricted system access

---

## Observability

The prototype uses lightweight structured JSON events.

Events include information such as:

- timestamp
- severity
- event type
- request ID
- customer ID when appropriate
- service
- function name
- success status
- duration
- structured details
- error information

Example:

```json
{
  "timestamp": "2026-08-22T16:29:08.591093Z",
  "level": "info",
  "event_type": "tool_call",
  "request_id": "req-123",
  "customer_id": "CUST-001",
  "service": "stepstep-support-agent",
  "function_name": "execute_tool",
  "success": true,
  "details": {
    "tool_name": "search_knowledge",
    "iteration": 2
  }
}
```

The implementation is intentionally lightweight for the prototype.

A production deployment could forward these events to a centralized observability platform and add metrics, dashboards, tracing, alerting, and retention policies.

Logs intentionally avoid unnecessary customer information such as email addresses, phone numbers, and complete conversation contents.

---

## API

The prototype is exposed through FastAPI.

### Health check

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

### Chat

```http
POST /api/v1/chat
```

Request:

```json
{
  "customer_id": "CUST-001",
  "message": "Can I cancel ORD-1001?"
}
```

Response:

```json
{
  "request_id": "req-d46d1891-bb4c-4b36-bc97-3ddcad9736b4",
  "response": "Your order ORD-1001 is eligible for cancellation..."
}
```

The API also exposes interactive documentation through FastAPI:

```text
http://127.0.0.1:8000/docs
```

---

## Project structure

```text
stepstep-support-agent/
│
├── app/
│   ├── agent/
│   │   ├── agent.py
│   │   ├── context.py
│   │   ├── prompts.py
│   │   └── tools.py
│
│   ├── api/
│   │   ├── routes.py
│   │   └── schemas.py
│
│   ├── domain/
│   │   └── orders.py
│
│   ├── repositories/
│   │   └── orders.py
│
│   ├── retrieval/
│   │   └── knowledge.py
│
│   ├── tools/
│   │   ├── knowledge.py
│   │   ├── orders.py
│   │   └── policies.py
│
│   ├── observability/
│   │   ├── events.py
│   │   └── logger.py
│
│   └── main.py
│
├── assessment/
│   └── ...
│
├── data/
│   ├── knowledge/
│   └── orders.json
│
├── scripts/
│   └── ...
│
├── tests/
│   └── ...
│
├── .env.example
├── .gitignore
├── DECISION_LOG.md
├── requirements.txt
└── README.md
```

---

# Setup

## Requirements

- Python 3.11+
- A Groq API key

The prototype uses Groq for LLM inference and a local Sentence Transformers model for embeddings.

No paid embedding service is required.

---

## 1. Clone the repository

```bash
git clone https://github.com/Shahid0324-GIT/stepstep-support-agent.git
cd stepstep-support-agent
```

## 2. Create a virtual environment

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure environment variables

Copy:

```text
.env.example
```

to:

```text
.env
```

Configure:

```env
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-20b
```

The `.env` file should never be committed to the repository.

---

## 5. Run the tests

```bash
python -m pytest -v
```

The test suite covers:

- Domain business rules
- Repository behavior
- Customer-scoped order access
- Tool behavior
- Knowledge retrieval
- Retrieval confidence thresholds
- API validation
- API responses
- Escalation behavior

---

## 6. Start the API

```bash
uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/docs
```

---

# Testing strategy

Testing is split between deterministic application behavior and real agent behavior.

### Deterministic tests

These cover components where the expected result should not depend on an LLM:

- Business rules
- Repository authorization
- Tool responses
- Retrieval threshold behavior
- API validation

### Agent evaluation

Real LLM scenarios are used to evaluate:

- Tool selection
- Knowledge grounding
- Unsupported requests
- Escalation
- Action-claim boundaries
- Multi-step tool use
- Out-of-domain handling
- Prompt-injection resistance

This distinction is intentional.

A test for a cancellation business rule should not require a network call to an LLM.

---

# Failure scenarios evaluated

The prototype was deliberately tested against failure cases rather than only successful examples.

| Scenario                                   | Expected behavior                  |
| ------------------------------------------ | ---------------------------------- |
| Customer requests their own order          | Return order                       |
| Customer requests another customer's order | Do not expose order                |
| Unknown order                              | Return not found                   |
| Processing order cancellation              | Report eligible                    |
| Shipped order cancellation                 | Report not eligible                |
| Delivered order cancellation               | Report not eligible                |
| Unsupported knowledge question             | Do not infer an answer             |
| Low-confidence retrieval                   | Do not return weak evidence        |
| Unsupported exchange request               | Escalate                           |
| Out-of-domain request                      | Do not invoke business tools       |
| Repeated knowledge searches                | Prevent runaway repetition         |
| Maximum tool iterations reached            | Stop safely                        |
| Cancellation eligibility                   | Do not claim cancellation occurred |

---

# Technical judgment

## 1. What did you decide was unsafe to automate, and why?

Business-critical decisions and destructive actions were considered unsafe to delegate directly to the LLM.

The LLM can interpret a request and select an appropriate tool, but deterministic application code decides whether a customer is authorized to access an order and whether a cancellation is permitted.

The prototype does not expose a destructive cancellation operation.

This prevents the model from turning a plausible conversational response into an unsupported business action.

---

## 2. What would most likely fail first in production, and how would you detect and contain it?

The most likely early failure is incorrect model behavior around tool selection or knowledge interpretation.

For example, the model may select the wrong tool, repeatedly call a tool, attempt to infer a workflow from related but insufficient knowledge, or misclassify an out-of-domain request.

The prototype contains this with:

- Explicit tool definitions
- Structured tool responses
- Retrieval similarity thresholds
- Repeated-tool-call protection
- Maximum tool iterations
- Deterministic business rules
- Escalation
- Explicit domain boundaries
- Structured observability

Production monitoring should additionally track tool-selection errors, escalation rates, retrieval false positives/negatives, latency, model failures, and customer outcomes.

---

## 3. What important architecture or product choices did you make, what alternatives did you reject, and what evidence informed those decisions?

The main architectural choice was to use a single controlled agent rather than a multi-agent system.

The domain is small enough that multiple agents would introduce coordination and failure modes without providing meaningful value.

Semantic retrieval was selected over keyword matching because customer questions may differ significantly from the wording in the knowledge base.

A managed vector database was rejected because the prototype corpus is small and in-memory retrieval is sufficient.

Business rules were kept outside the LLM because deterministic rules are easier to test and reason about.

Customer-scoped order retrieval was introduced after recognizing that an `order_id` alone would create an authorization boundary problem.

A separate domain-classification component was not introduced because the current domain is small and the additional routing layer would add complexity without sufficient evidence that it was necessary.

These decisions and the evidence behind them are recorded in `DECISION_LOG.md`.

---

## 4. What did an AI tool suggest or generate that you rejected, corrected, or improved?

AI coding tools were used during implementation, including for test generation and implementation assistance.

Generated code was reviewed and tested rather than accepted blindly.

A significant example occurred during agent evaluation.

For an unsupported exchange request, the model initially inferred an exchange workflow from the returns policy. The proposed workflow included returning the original product, waiting for a refund, and placing a new order.

That workflow was not present in the knowledge base.

The behavior was treated as a defect rather than accepted as a plausible answer.

The system was subsequently changed to:

- enforce retrieval thresholds
- prevent repeated identical tool calls
- explicitly prohibit unsupported policy inference
- provide an escalation tool
- add application-level knowledge-gap enforcement
- add regression coverage for the unsupported scenario

A second evaluation exposed an out-of-domain failure where an unrelated request was routed into the support workflow. The domain boundary was strengthened and dedicated out-of-domain regression scenarios were added.

---

## 5. What evidence makes you trust the system today, what remains unproven, and what would you improve first with one additional day?

Current confidence comes from:

- Passing deterministic unit tests
- Passing API tests
- Retrieval evaluation
- Customer authorization tests
- Real LLM end-to-end scenarios
- Observed escalation behavior
- Observed containment of repeated tool calls
- Out-of-domain evaluation scenarios
- Structured logs showing the agent/tool execution path

The system is still a prototype and broad production reliability is unproven.

The main limitations are:

- Small knowledge corpus
- Small evaluation dataset
- Local in-memory embeddings
- Fixture-based order storage
- Prototype authentication boundary
- No persistent support-ticket system
- No production observability platform
- LLM behavior remains model-dependent

With one additional day, the highest-value improvement would be expanding the evaluation suite with a larger set of labeled normal, ambiguous, unsupported, adversarial, authorization-boundary, knowledge-gap, and out-of-domain scenarios.

I would use those results to measure retrieval precision/recall, escalation quality, tool-selection failures, and unsafe response rates rather than simply adding more infrastructure.

---

# Known limitations

This project is intentionally a prototype.

### Authentication

`customer_id` is supplied by the API request and represents simulated authenticated context.

A production system would derive the customer identity from a verified authentication token or session.

### Persistence

Orders and escalation records use local fixture/in-memory data.

A production system would use persistent storage and a real support-ticket or case-management system.

### Knowledge retrieval

The current knowledge corpus is small and documents are embedded as whole documents.

A larger system would likely require:

- Document chunking
- Metadata
- Persistent indexes
- Retrieval evaluation datasets
- Potential reranking
- Potential managed vector storage

### Observability

The prototype writes structured events locally.

A production system would forward those events to centralized logging and monitoring infrastructure.

### Model dependency

The system remains dependent on the selected LLM's ability to follow instructions and select tools correctly.

Application-level controls are therefore treated as mandatory rather than relying solely on prompting.

---

# Why there is no Docker setup

Containerization was intentionally not added for this prototype.

The assessment is focused on agent behavior, safety boundaries, testing, observability, and engineering judgment. Adding container orchestration or additional infrastructure would increase complexity without materially improving the demonstrated behavior.

The application is designed to run directly from a Python virtual environment.

A production deployment could containerize the service once deployment requirements justify it.

---

# AI usage disclosure

AI tools were used as development assistants during the project.

They were used for:

- Code suggestions
- Test scaffolding
- Syntax assistance
- Exploring implementation approaches
- Reviewing implementation ideas

AI-generated output was reviewed and tested before being incorporated.

Generated code was modified when it did not match the intended architecture or behavior.

One example was the use of generated `pytest.mark.parametrize` tests. The generated tests were reviewed and adapted while learning the testing pattern rather than treating the generated code as authoritative.

The most important example was not accepting model behavior during agent evaluation. The model generated an unsupported exchange workflow from a related returns policy. That behavior was identified as unsafe and became the basis for a defect, corrective controls, and regression testing.

A later out-of-domain evaluation also exposed that an unrelated request could enter the support workflow. That behavior was treated as a boundary defect, leading to explicit domain constraints and dedicated regression scenarios.

The project therefore treats AI as an implementation accelerator, not as the authority for architecture, security, business rules, or correctness.

---

# Decision log

Detailed engineering decisions, rejected alternatives, discovered defects, and corrective actions are maintained in:

[`DECISION_LOG.md`](DECISION_LOG.md)

The decision log was maintained during development rather than written retrospectively.

---

# Project status

Prototype complete.

The current implementation prioritizes:

- Safe AI behavior
- Deterministic business boundaries
- Customer-scoped access
- Knowledge grounding
- Failure handling
- Human escalation
- Out-of-domain boundaries
- Structured observability
- Testability
- Clear engineering trade-offs

The next production steps would be driven by measured evaluation results rather than by adding infrastructure prematurely.
