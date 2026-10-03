# Privacy Policy

**Effective date:** October 3, 2026

This Privacy Policy describes data handling by the Proof-of-Intent Gateway software (the "Gateway"). The organization that deploys and operates a Gateway instance determines its purposes, hosting, logging, retention, and legal obligations. This policy describes the behavior of the Gateway application in this project; a deployment operator must update it if its infrastructure or practices differ.

## Data processed

When you call `POST /v1/proxy/execute`, the Gateway receives the target URL, caller-supplied headers, request body, current and proposed state hashes, and proof data. It processes these values in memory to validate the request and proof. If validation succeeds, it forwards the request body and permitted caller-supplied headers to the configured upstream destination. The state hashes and proof are used for verification and are not included in the forwarded request by this implementation. Upstream response data is returned to the caller.

Do not include personal information, credentials, or confidential data unless you are authorized to do so and have assessed the security and privacy obligations of both the Gateway operator and the selected upstream provider. Caller-supplied headers may contain credentials and are sent to the selected destination, except for hop-by-hop and connection-specific headers.

## Logs and retention

The Gateway application does not write execution payloads, proofs, or client IP addresses to persistent storage. Request data is held in process memory while the request is handled and is then eligible for release; this is not a guarantee about operating-system memory, crash dumps, or infrastructure outside the application.

The ASGI server, reverse proxy, load balancer, hosting platform, or security tooling may record client IP addresses, request paths, timestamps, status codes, and other operational metadata. For example, Uvicorn access logging can record the connecting client address and request line. These logs are controlled by the deployment operator, not by this application; their contents, access, and retention depend on that operator's configuration. Operators should disable or minimize unnecessary logs, prevent request bodies and secrets from entering logs, restrict access, and set an appropriate retention period.

## Transit and upstream routing

The Gateway accepts only HTTPS target URLs whose exact hostnames are configured in `POI_ALLOWED_HOSTS`, and it does not follow redirects. This restricts routing but does not make an upstream provider part of the Gateway operator or establish that provider's privacy practices. Upon successful authorization, the request body and permitted headers are sent to the selected upstream host over HTTPS. That provider may independently collect, use, or retain information under its own terms and privacy notice. Review the destination and its terms before sending data.

The caller-to-Gateway connection should also use HTTPS through a trusted ingress in production. This application does not itself configure public TLS termination, authenticate callers, or control network-level routing outside the configured target-host check.

## Sharing and service providers

The Gateway shares forwarded request data with the upstream destination selected by the caller, after policy and proof checks pass. The deployment operator's hosting, ingress, logging, and monitoring providers may process connection or operational data as part of providing those services. The Gateway project does not include analytics or an application-level data store. Operators should identify their actual providers and any cross-border processing in deployment-specific notices.

## Your choices and contact

Do not send data to the Gateway if you are not authorized to do so. Requests to access, correct, or delete data should be directed to the organization operating the Gateway, which can identify the relevant infrastructure and logs. Contact [Proof-of-Intent Gateway Support](mailto:support@proof-of-intent.example); the hosted operator must replace this reserved example address with a monitored contact before public deployment.

## Policy changes

The operator may revise this policy to reflect changes in the Gateway or its deployment. The effective date above identifies the latest version published with this software.