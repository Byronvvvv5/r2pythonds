Plan: Private Networking POC Stages

Use the current resource-group Bicep deployment flow as the backbone for three staged increments. Stage 1 adds the VNet, private endpoints, private DNS, and Function outbound integration needed to make Storage and Cosmos private while preserving Function connectivity. Stage 2 adds Function inbound private access and a concrete internal-user test path. Stage 3 keeps API Management on Consumption but completes the reusable APIM configuration work that is independent of the eventual APIM tier, while explicitly excluding private backend connectivity that Consumption cannot support.

Steps

Stage 1, data private only: add a reusable networking slice to infra/main.bicep, including a VNet plus separate subnets for private endpoints and Function outbound integration. This is the first dependency because later stages build on the same network.

Stage 1, storage: extend infra/modules/storage.bicep or wrap it with a new private-endpoint module so both storage accounts created from infra/main.bicep can receive private endpoints for the required subresources. Minimum expectation: blob for the data account, and the required subresources for the Function host/deployment account used by AzureWebJobsStorage and package deployment.

Stage 1, Cosmos: extend infra/modules/cosmos.bicep to support private endpoint mode for the SQL API endpoint and disable public network access only after the private endpoint and DNS path are in place.

Stage 1, DNS: add private DNS zones and VNet links through Bicep for the services introduced above. Keep DNS resources in a dedicated module if that makes the main template easier to manage. Preserve the existing app settings that point to normal service hostnames so private routing happens through DNS instead of code changes.

Stage 1, Function outbound: update infra/modules/functionApp.bicep to enable outbound VNet integration for the Flex Consumption Function App and ensure the integration subnet is delegated correctly for that hosting model. Reuse the existing managed identity pattern and role assignments.

Stage 2, Function inbound private: add a private endpoint for the Function App HTTP surface and the required private DNS records, while keeping outbound integration from Stage 1 intact. This depends on Stage 1 because the internal-user test path relies on the VNet.

Stage 2, controlled transition: add a reversible transition for public access in infra/modules/functionApp.bicep. Start with coexistence mode or access restrictions during validation, then move to private-only inbound if the internal-user flow works.

Stage 2, internal-user model: define the internal-user access path explicitly. Corporate VPN or a test VM inside the VNet or a peered VNet must be able to resolve the Function hostname to the private endpoint and invoke the HTTP trigger. Do not assume “same organization” is enough without routing and DNS.

Stage 2, verification: test Function HTTP access from an internal network path and from a public network path. Success criteria are that internal clients can resolve and call the endpoint, while public clients cannot call it directly.

Stage 3, APIM on Consumption: keep the APIM SKU in infra/modules/apim.bicep as Consumption, but expand the Bicep so it manages the API surface as far as the tier allows. This stage can proceed without changing the APIM tier.

Stage 3, fuller APIM resources: in infra/modules/apim.bicep, replace the current minimal API shell with fuller APIM resources: backend definition, API definition import strategy, policy resources, product resources, subscription requirements, and named values where appropriate.

Stage 3, API definition source: choose an API definition source that can be automated in the repo. If the Function app can expose OpenAPI consistently, import it. If not, store and version an OpenAPI document in the repo and import that through Bicep. Make this decision before implementing policies and products so operation names and routes stay stable.

Stage 3, gateway behavior: add inbound policies and consumer model basics that are reusable across tiers, such as request validation, header handling, rate limiting or quotas where supported, backend routing policy, product grouping, and subscription enforcement. Keep backend authentication realistic for the current backend path, but do not attempt to prove private backend reachability through APIM while the tier remains Consumption.

Stage 3, verification: validate and deploy APIM changes through the existing Bicep workflow, then confirm the API import, product, subscription, and policy behavior using the public Function backend path that still exists for this stage. Treat this as gateway-configuration validation, not final private-network validation.

Decision gate after Stage 3: use the POC outputs to decide whether APIM should remain a public gateway over a restricted Function, or whether the next increment must upgrade APIM to Developer, Standard v2, or Premium so APIM can reach private backends directly.

Relevant files

infra/main.bicep — entrypoint to wire in VNet, private endpoint modules, DNS, and staged dependencies.
infra/modules/storage.bicep — current storage account deployment that needs private-endpoint and network-rule support.
infra/modules/cosmos.bicep — current Cosmos deployment with public access enabled, to be extended for private endpoint mode.
infra/modules/functionApp.bicep — Function Flex Consumption plan, runtime/deployment storage settings, and the place to add outbound integration and later inbound private access.
infra/modules/apim.bicep — current minimal Consumption APIM definition to be expanded for API import, policies, products, and backend modeling.
infra/modules/roleAssignments.bicep — existing RBAC pattern to preserve for managed identity access after private networking is introduced.
infra/parameters/dev.parameters.json — dev-stage toggles and rollout controls for private networking.
.github/workflows/infra.yml — existing validate, what-if, deploy workflow that should remain the primary deployment path.
api/function_app.py — confirms the app already uses managed identity and normal service endpoints, which supports DNS-based private routing without code redesign.
infra/README.md — should be updated once the staged networking deployment story is finalized, if documentation updates are included later.

Decisions

Included in Stage 1: private endpoints, DNS, VNet integration, and public data shutdown for Storage and Cosmos.
Included in Stage 2: Function inbound private access and internal-user connectivity validation.
Included in Stage 3: APIM configuration maturity through Bicep while staying on Consumption.
Excluded from Stage 3: APIM private backend connectivity validation, because Consumption cannot connect to VNet-isolated backends.
Recommended implementation order is strict: Stage 2 depends on Stage 1 network primitives; Stage 3 can begin with public backend assumptions but should not be treated as proof of the final APIM networking architecture.