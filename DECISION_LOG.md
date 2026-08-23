# Decision Log

This document records significant engineering decisions made during
development, the alternatives considered, the reasoning behind them,
and the evidence available at the time of the decision.

The log is intentionally maintained during development rather than
written retrospectively.

---

## D001 — Keep business rules outside the LLM

**Status:** Accepted

### Decision

Business rules such as cancellation and return eligibility will be
implemented as deterministic application logic rather than delegated
to the LLM.

### Why

The LLM is probabilistic and should not be the authority for
transactions or policy enforcement.

The model can interpret the customer's request and select appropriate
tools, but application code must determine whether an action is
permitted.

### Alternatives considered

- Allow the LLM to determine eligibility from policy documents.
- Encode the rules entirely in the system prompt.

### Why rejected

Both approaches make critical business decisions dependent on model
behavior and make the system harder to test deterministically.

### Evidence

Cancellation rules are implemented as domain logic and covered by unit
tests for processing, shipped, delivered, and cancelled orders.

### Consequence

The agent requires a clear boundary between probabilistic reasoning and
deterministic business logic.

---

## D002 — Customer-scoped order retrieval

**Status:** Accepted

### Decision

Order lookup requires both an order ID and customer ID:

`get_order(order_id, customer_id)`

### Why

Knowing an order ID must not be sufficient to retrieve another
customer's order.

Authorization must be enforced at the data-access boundary rather than
being left to the LLM or prompt instructions.

### Alternatives considered

- `get_order(order_id)` with authorization handled by the agent.
- Allow the LLM to determine whether an order belongs to the customer.

### Why rejected

Both approaches rely on higher-level behavior to enforce a security
boundary that should be deterministic.

### Evidence

Tests verify that a customer can retrieve their own order but receives
no order data when requesting another customer's order.

### Security behavior

An unknown order and an order belonging to another customer both return
the same external result: no order found.

This avoids revealing whether another customer's order exists.

---

## D003 — Separate repositories from agent tools

**Status:** Accepted

### Decision

Data access and agent-facing capabilities are separated into different
layers.

The repository is responsible for retrieving order data, while the
tool provides a controlled interface for the agent.

### Structure

Repository:

`app/repositories/orders.py`

Agent-facing tool:

`app/tools/orders.py`

### Why

The repository should not depend on the existence of an LLM.

The tool layer provides a controlled boundary where agent-specific
behavior, validation, observability, and response shaping can be added
without coupling those concerns to data access.

### Consequence

The same repository can later be used by an API, background process, or
other application component without requiring an AI agent.

---

## D004 — Use structured tool responses

**Status:** Accepted

### Decision

Agent tools return explicit Pydantic response models rather than raw
domain objects or unstructured strings.

For example, the order tool returns:

`OrderToolResponse`

with:

- `found`
- `order`

### Why

The LLM benefits from predictable structured tool output.

It also makes tool behavior easier to test and prevents the agent from
having to infer whether a missing value represents a failed lookup,
missing data, or an actual empty result.

### Alternatives considered

- Return `Order | None`.
- Return plain dictionaries.
- Return human-readable strings.

### Why rejected

`Order | None` provides insufficient context to the agent.

Plain dictionaries and strings provide less schema enforcement and make
the interface less explicit.

### Evidence

Tool tests cover successful order lookup, unknown orders,
cross-customer access, and preservation of nested order items.

---

## D005 — Scenario-driven fixture data

**Status:** Accepted

### Decision

Use a small, deliberately designed fixture dataset rather than a large
synthetic dataset.

### Coverage

The current order fixtures cover scenarios including:

- cancellable processing orders
- shipped orders
- delivered orders
- return-window cases
- final-sale products
- multiple-item orders
- cancelled orders
- shipping/tracking scenarios
- damaged-item escalation scenarios
- cross-customer authorization testing

### Why

The assessment evaluates behavior and engineering judgment rather than
the realism or volume of sample data.

Each fixture should exist because it exercises a workflow, boundary, or
failure mode.

### Consequence

New fixtures will be added only when they provide meaningful test or
evaluation coverage.

---

## D006 — Simulate authentication at the prototype boundary

**Status:** Accepted

### Decision

The prototype uses `customer_id` supplied in the request context to
simulate the identity of the authenticated customer.

A complete authentication system such as JWT or OAuth is outside the
scope of the prototype.

### Why

The assessment focuses on agent behavior, authorization boundaries,
retrieval, controls, and reliability.

Implementing a full identity provider would add significant scope
without materially improving the assessment.

### Important limitation

A client-provided customer ID is not a secure authentication mechanism.

In production, the customer ID must be derived from a verified
authentication token or session.

### Security requirement

Regardless of how identity is established, the order repository must
continue to enforce customer-scoped access.

---

## D007 — Use embedding-based knowledge retrieval

**Status:** Accepted

### Decision

Use semantic embeddings for knowledge retrieval rather than simple
keyword matching.

The prototype uses the local `sentence-transformers` model
`all-MiniLM-L6-v2` with in-memory similarity search.

A managed vector database will not be introduced for the prototype.

### Why

Customer questions may use wording that differs significantly from the
knowledge source.

Semantic embeddings allow conceptually similar questions to retrieve
relevant knowledge even when exact keywords differ.

The knowledge corpus is small, so local retrieval is sufficient for the
prototype.

### Alternatives considered

- Keyword-based retrieval
- Managed vector database
- Paid embedding APIs

### Why rejected

Keyword retrieval may fail when customer wording differs from the source
material.

A managed vector database would add operational complexity without
meaningful value for the current corpus size.

Paid embedding APIs conflict with the project's zero-cost constraint.

### Evidence

The embedding model successfully downloaded and loaded locally.

The initial retrieval tests passed for:

- return policy queries
- cancellation policy queries
- shipping policy queries
- empty queries

### Current limitation

Retrieval quality has not yet been evaluated across a sufficiently broad
or adversarial evaluation set.

The current implementation also embeds whole documents because the
initial knowledge files are small and self-contained.

### Future improvement

If the knowledge corpus grows, document chunking, persistent indexes,
metadata filtering, and/or a managed vector store can be evaluated
based on measured retrieval requirements.

---

## D008 — Lightweight structured observability

**Status:** Accepted

### Decision

Use a lightweight structured logging layer based on Pydantic event
models and JSON output.

Each significant operation can produce a structured event containing:

- timestamp
- level
- event type
- request ID
- customer ID when appropriate
- service
- function name
- success status
- duration
- structured details
- error information when applicable

### Why

The assessment explicitly evaluates observability and production
readiness.

Structured events make it possible to correlate operations and
diagnose failures without relying on unstructured console messages.

### Inspiration

The structure is influenced by production logging patterns encountered
in previous engineering work, including correlation IDs, function names,
severity levels, structured metadata, events, and centralized logging.

The prototype intentionally implements only the subset needed for this
assessment.

### Alternatives considered

- `print()` statements
- unstructured Python log messages
- a full external observability stack such as Datadog or Application
  Insights

### Why rejected

Plain text logs make correlation and automated analysis more difficult.

A complete external observability platform would add infrastructure
without meaningful benefit for the assessment prototype.

### Privacy consideration

Logs should avoid unnecessary customer information such as email
addresses, phone numbers, and complete conversation contents.

Identifiers required for debugging and request correlation may be
logged.

### Future improvement

Production deployment could forward the same structured events to a
centralized observability platform with dashboards, alerts, metrics,
tracing, and retention policies.

---

## D009 — Controlled single-agent architecture

**Status:** Accepted

### Decision

Use a single LLM-powered support agent with a small set of explicitly
defined tools.

The LLM is responsible for:

- interpreting customer requests
- selecting appropriate tools
- generating the final response

Deterministic application code remains responsible for:

- authorization
- business rules
- policy enforcement
- action boundaries
- escalation decisions where required

### Why

A single controlled agent is sufficient for the support domain and is
easier to test, observe, and reason about than a multi-agent system.

### Alternatives considered

- Multi-agent architecture
- Fully autonomous agent with unrestricted tool access
- Traditional deterministic intent routing without LLM reasoning

### Why rejected

Multiple agents would introduce coordination and additional failure
modes without providing meaningful value for this prototype.

Unrestricted autonomy would make authorization and business-critical
behavior harder to control.

Purely deterministic intent routing would reduce the system's ability
to handle natural-language variation and demonstrate meaningful AI
tool use.

### Control boundary

The LLM does not control authenticated customer identity.

When the model requests an order lookup, the application supplies the
customer context to the order tool.

The LLM therefore controls the requested order ID but not the
authorization identity.

### Consequence

The system can use LLM reasoning while keeping security and
business-critical decisions outside the model.

## D010 — Use Groq GPT-OSS 20B for agent inference

**Status:** Accepted

### Decision

Use `openai/gpt-oss-20b` through Groq as the LLM for the prototype.

### Why

The model supports tool use, function calling, reasoning, and structured
output capabilities required by the support-agent workflow.

The model also provides very high inference speed through Groq, which is
useful for a multi-step tool-calling workflow.

### Alternatives considered

- GPT-OSS 120B
- Smaller lightweight models
- Groq Compound systems

### Why rejected

GPT-OSS 120B provides greater capability but is unnecessary for the
small and constrained support domain. The additional model capacity
would not compensate for weaknesses in our application-level controls.

Groq Compound was not selected because the prototype needs explicit
control over its own knowledge retrieval and business tools rather than
delegating orchestration to a broader built-in system.

### Control strategy

The model will only have access to explicitly defined application
tools. It will not have arbitrary web access, code execution, or
unrestricted system capabilities.

### Reliability constraint

The agent loop will enforce a maximum number of tool iterations to
prevent runaway tool-calling behavior.

### Known limitation

The prototype's behavior remains dependent on the selected model's
tool-selection and instruction-following capabilities. This will be
tested through the evaluation suite rather than assumed from model
capability claims.

## D011 — Validate agent behavior through scenario-based evaluation

**Status:** Accepted

### Decision

Evaluate the agent using scenario-based tests covering normal behavior,
authorization boundaries, unsupported requests, and adversarial
instructions.

The evaluation will distinguish between deterministic application
behavior and LLM behavior.

### Initial scenarios

The first manual scenarios covered:

- Authorized order lookup
- Cross-customer order access
- Knowledge-based shipping question
- Unsupported request
- Prompt injection attempting to access another customer's order

### Initial evidence

The agent successfully:

- retrieved information for the authorized customer
- prevented cross-customer order disclosure
- answered the shipping question using the knowledge source
- declined the unsupported weather request
- resisted the initial prompt injection attempt

### Why

A successful response alone does not demonstrate system reliability.

Testing explicit failure and adversarial scenarios provides evidence
about the control boundaries around the LLM.

### Testing strategy

Deterministic unit tests will cover business rules, repositories, and
tools.

Agent orchestration will be tested using mocked or fake model responses
where deterministic behavior is required.

A smaller integration evaluation will exercise the real LLM to measure
tool selection and end-to-end behavior.

### Known limitation

The initial results are manual observations from a small scenario set.
They do not yet establish broad reliability.

The evaluation set will be expanded before submission.

## D012 — Prevent unsupported action claims

**Status:** Accepted

### Decision

The agent must not claim that a customer-support action was completed
unless an application tool explicitly reports that the action succeeded.

For cancellation, the prototype exposes deterministic cancellation
eligibility evaluation but does not expose an order-mutating cancellation
operation.

### Defect discovered

During an end-to-end test for:

`Can I cancel ORD-1001?`

the agent retrieved the order and cancellation policy and produced:

> "I'll proceed with the cancellation for you."

No cancellation operation existed in the application.

The model therefore implied that an action could be performed despite the
application having no capability to perform that action.

### Root cause

The LLM generated a plausible conversational continuation that exceeded
the capabilities exposed by the application.

The system prompt contained a prohibition against claiming completed
actions, but the capability boundary was not sufficiently explicit.

### Corrective action

A deterministic `evaluate_cancellation` tool was introduced.

The tool:

1. Performs customer-scoped order lookup.
2. Applies the deterministic cancellation business rule.
3. Returns whether cancellation is permitted.
4. Does not mutate the order.

The system prompt was updated to explicitly distinguish between
eligibility evaluation and actual cancellation.

The agent is instructed never to claim that an action occurred unless an
application tool explicitly confirms successful completion.

### Evidence

After the change, the same scenario produced a response stating that
the order was eligible for cancellation while explicitly stating that
the system had not cancelled the order.

### Regression test

An agent evaluation will verify that cancellation eligibility does not
result in a claim that cancellation was completed.

### Consequence

The model can reason about and communicate supported actions without
being given unrestricted mutation authority.

## D013 — Introduce a minimum retrieval similarity threshold

**Status:** Accepted

### Decision

Introduce a minimum cosine-similarity threshold of `0.50` for knowledge
retrieval.

Documents below this threshold will not be returned to the agent.

### Problem discovered

During retrieval evaluation, clearly relevant questions produced strong
similarity scores:

- Shipping question: `0.6780`
- Cancellation question: `0.6304`
- Returns question: `0.5654`

However, an unsupported question:

`Can I change the color of my shoes after delivery?`

returned a returns-policy document with a similarity score of `0.4171`.

Although the result was semantically related to footwear returns, it did
not directly answer the customer's question.

Returning this document to the LLM could encourage an unsupported answer
by causing the model to infer that the returns policy also governs
product-color changes.

### Evidence

A small retrieval evaluation produced the following highest similarity
scores:

| Query                                              | Highest Score | Classification |
| -------------------------------------------------- | ------------: | -------------- |
| How long does standard shipping take?              |        0.6780 | Relevant       |
| What is the return policy?                         |        0.5654 | Relevant       |
| Can I cancel my order?                             |        0.6304 | Relevant       |
| Can I change the color of my shoes after delivery? |        0.4171 | Unsupported    |
| What is the weather in Singapore today?            |        0.0607 | Unsupported    |
| Can you tell me a joke?                            |        0.0735 | Unsupported    |

### Rationale

A threshold of `0.50` separates the currently observed relevant
questions from the unsupported scenarios in the evaluation set.

The threshold is treated as a prototype heuristic rather than a
universally valid semantic boundary.

### Alternatives considered

- Return the top-k results regardless of similarity.
- Use keyword matching.
- Use a more complex reranking model.
- Use an external vector database.

### Why rejected

Returning top-k results without a relevance threshold can provide weak
evidence to the LLM and increase the risk of unsupported answers.

Keyword matching is less robust to natural-language variation.

A reranking model would add complexity that is unnecessary for the small
prototype corpus.

A managed vector database would not address the relevance problem by
itself and would add unnecessary infrastructure.

### Corrective action

Knowledge retrieval now filters results below the minimum similarity
threshold before returning them to the agent.

Regression tests were added for:

- an unrelated weather question
- an unsupported product-change question

### Known limitation

The threshold was selected using a small evaluation set and has not been
validated against a large production-like query distribution.

A production system should calibrate the threshold using a representative
evaluation dataset, including false-positive and false-negative
retrieval analysis.

### Future improvement

Build a larger labeled retrieval evaluation set and measure:

- precision
- recall
- false-positive retrievals
- false-negative retrievals

A reranker could be evaluated if the knowledge corpus becomes larger or
the retrieval quality becomes insufficient.

# D014 — Escalate unresolved requests instead of inferring unsupported workflows

**Status:** Accepted

## Defect discovered

During an end-to-end test for:

> I want to exchange ORD-1001 for a different size.

the knowledge base did not contain an exchange policy.

The retrieval layer correctly returned no sufficiently relevant knowledge. However, the LLM initially retried the knowledge search multiple times and eventually generated an unsupported exchange workflow based on the returns policy.

The generated response suggested returning the original pair, waiting for a refund, and placing a new order for the requested size. This workflow was **not explicitly supported by the knowledge base**.

## Risk

The response was plausible and related to the available returns policy, but the specific exchange workflow was not established by the source material.

This creates a particularly dangerous failure mode because a response can appear grounded while still inventing a business process.

## Root cause

The retrieval threshold successfully prevented low-confidence documents from being returned, but the LLM could still reinterpret related policy information and construct an unsupported workflow.

The agent could also repeatedly invoke the same knowledge-search operation when no relevant information was available.

## Corrective actions

The following controls were introduced:

1. The knowledge tool explicitly reports when no sufficiently relevant information is available.
2. The system prompt prohibits combining or reinterpreting related policies into unsupported business rules.
3. The system prompt instructs the agent to escalate when sufficient customer information is available but the issue cannot be safely resolved.
4. The application tracks tool name and arguments and blocks repeated identical tool calls.
5. The agent has an explicit `escalate_to_support` tool for human handoff.

## Iteration evidence

**Before the corrective changes:**

```text
search_knowledge
→ search_knowledge
→ search_knowledge
→ search_knowledge
→ search_knowledge
→ iteration limit
```

The application safely stopped the loop, but the behavior did not provide a proper escalation path.

After strengthening the prompt and adding the application-level tool-repeat protection, the agent stopped inventing the exchange workflow.

## Final end-to-end result

With the customer providing the order ID:

> I want to exchange ORD-1001 for a different size.

the agent produced the following tool flow:

```text
search_knowledge
        ↓
no sufficiently relevant exchange policy
        ↓
escalate_to_support
        ↓
agent_response
```

The resulting response explicitly stated that the exchange policy could not be found and that the request had been escalated to support.

This demonstrates the intended safety boundary:

```text
Known information
    → answer

Missing required information
    → clarify

Sufficient information but unresolved safely
    → escalate
```

## Regression coverage

The escalation path is now tested through an end-to-end scenario involving an unsupported exchange request.

The existing test suite also continues to cover:

- knowledge retrieval
- retrieval threshold behavior
- order authorization
- deterministic cancellation rules
- tool behavior
- escalation behavior

## Consequence

The agent is no longer required to manufacture an answer when the knowledge base cannot safely resolve a request.

Human escalation is represented as an actual tool operation rather than merely a conversational suggestion, allowing the handoff to be observed and tested.

## Known limitation

The current escalation implementation stores escalation records in memory because this is a prototype.

A production implementation would persist the escalation in a support-ticket system or queue and provide operational ownership, status tracking, retry handling, and monitoring.

## Future improvement

A production system should additionally evaluate escalation quality using a larger set of scenarios, including refunds, damaged products, payment disputes, and other cases where human intervention is required.

## D015 — Keep out-of-domain requests outside the support workflow

**Status:** Accepted

### Defect discovered

During evaluation of the StepStep Support Agent, we added an out-of-domain
evaluation suite covering requests unrelated to StepStep customer support.

The initial scenarios behaved correctly:

- Weather requests were rejected without tool calls.
- General programming questions were rejected without tool calls.
- Travel questions were rejected without tool calls.
- Financial questions were rejected without tool calls.

However, an unrelated product request exposed a boundary issue:

`Can you recommend a laptop for software development?`

The agent incorrectly treated the request as a StepStep knowledge question,
called `search_knowledge`, failed to find relevant information, and then
escalated the request.

This was incorrect because the request was not a StepStep customer-support
request in the first place. Escalation is appropriate for an in-domain
request that cannot be safely resolved, not for an unrelated request outside
the agent's capabilities.

A second test confirmed that merely mentioning StepStep could trigger the
same behavior:

`Can you recommend a laptop for my StepStep work?`

The agent initially interpreted the StepStep reference as sufficient context
to enter the support workflow, despite the actual request being for a
general laptop recommendation.

### Root cause

The system prompt defined the agent's supported domain, but the boundary was
not explicit enough about requests that mention StepStep while asking for an
unrelated service or product.

The existing knowledge-gap guard correctly escalated requests when relevant
StepStep knowledge was unavailable. However, it could not distinguish between:

1. A legitimate StepStep support request with missing knowledge.
2. An unrelated request that happened to contain StepStep-related wording.

This meant that an out-of-domain request could incorrectly enter the
knowledge-retrieval and escalation workflow.

### Decision

Keep the domain boundary in the system prompt and explicitly instruct the
agent that:

- It only handles StepStep customer-support requests.
- Out-of-domain requests must not invoke business tools.
- Mentioning StepStep does not make an otherwise unrelated request
  StepStep-related.
- Out-of-domain requests should receive a clear capability-boundary response
  rather than escalation.

We deliberately did not introduce a separate classifier, additional LLM
call, keyword-based routing layer, or another retrieval model.

For the scope of this prototype, that would add complexity without enough
evidence that the additional machinery was necessary.

### Fix

The system prompt was strengthened to explicitly define the supported domain
and distinguish out-of-domain requests from in-domain knowledge gaps.

The agent is now instructed to avoid tools when a request is unrelated to
StepStep customer support.

The existing knowledge-gap escalation behavior remains unchanged for
legitimate StepStep requests.

This preserves the following boundary:

    StepStep request
          |
          +-- Knowledge available --> Answer
          |
          +-- Knowledge unavailable --> Escalate


    Unrelated request
          |
          +-- Capability-boundary response
              No business tools
              No escalation

### Regression testing

A dedicated automated out-of-domain evaluation suite was added covering:

- Weather
- General programming
- Travel
- Financial advice
- Unrelated product recommendations
- An unrelated request containing the word "StepStep"

The suite also records the agent event trace and asserts that out-of-domain
requests produce no business tool calls.

After the fix:

**6/6 out-of-domain scenarios passed.**

The final evaluation confirmed that all six scenarios returned explicit
capability-boundary responses and made no tool calls. :contentReference[oaicite:0]{index=0} :contentReference[oaicite:1]{index=1}

The evaluation results were also persisted to:

`assessment/out_of_domain_results.json` :contentReference[oaicite:2]{index=2}

### Why this matters

The distinction between an out-of-domain request and a knowledge gap is an
important safety boundary.

An agent should not escalate every question it cannot answer. Escalation
should represent a legitimate customer-support request that requires human
assistance.

For unrelated requests, the safer and more predictable behavior is to state
the agent's capability boundary explicitly.

### Alternatives rejected

#### Separate intent classifier

Rejected because it would introduce another model/component and another
failure mode for a relatively small prototype.

#### Keyword-based domain detection

Rejected because domain membership cannot reliably be determined from the
presence or absence of words such as `StepStep`.

For example, a request can mention StepStep while still being unrelated to
customer support.

#### Escalating every unknown request

Rejected because it conflates two different cases:

- "This is a StepStep request, but we don't know how to safely handle it."
- "This isn't a StepStep support request."

The first should escalate; the second should stop at the capability boundary.

### Evidence

The final automated evaluation produced:

```text
All out-of-domain cases passed.
Results saved to: assessment\out_of_domain_results.json
```

with zero business tool calls for all six scenarios.

Result

D015 establishes a clear separation between:

Out-of-domain requests → capability-boundary response
In-domain knowledge gaps → escalation

The regression suite now protects this boundary against future changes.

---

# Engineering Notes

This section records observations made during development.

## 2026-08-22

I initially considered implementing the project around an agent framework
immediately.

I decided to build the domain, repository, and tool layers independently
first so that the LLM would not become a dependency for testing core
business behavior.

I initially thought of order retrieval as simply:

`get_order(order_id)`

During design, I recognized that knowing an order ID should not be
sufficient to access another customer's order.

This led to customer-scoped retrieval:

`get_order(order_id, customer_id)`

The repository and agent tool were then kept separate so that data access
would not depend on the AI layer.

The current implementation uses fixture data rather than a database
because the assessment focuses on agent behavior, controls,
observability, retrieval, and engineering judgment rather than
persistence infrastructure.

I also chose to test the domain, repository, tool, and retrieval layers
independently before introducing the LLM. This should make it possible
to distinguish deterministic application failures from retrieval or
generation failures later in the evaluation.

The local embedding model was successfully downloaded and loaded.
Initial retrieval tests passed for the core policy queries.

The prototype is intentionally being developed incrementally so that
each layer can be tested before becoming a dependency of the next layer.

```

```
