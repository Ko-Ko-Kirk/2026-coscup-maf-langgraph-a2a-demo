Review this proposed enterprise customer-support architecture:

- A model-driven agent classifies complaints and may issue refunds up to USD 5,000.
- Tool calls write directly to the payment service.
- The service retries a failed request up to three times.
- Conversation state is stored in process memory.
- A separate LangGraph agent maintained by another team performs policy review.
- The services communicate over A2A.

Decide whether the design is ready for production and list the controls required before launch.

