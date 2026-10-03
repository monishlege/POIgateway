# Terms of Service

**Effective date:** October 3, 2026

These Terms of Service ("Terms") govern access to and use of the Proof-of-Intent Gateway API (the "Service"). By sending a request to or using the Service, you agree to these Terms. If you use the Service for an organization, you represent that you are authorized to bind that organization; "you" then refers to that organization.

## 1. Service and authorization

The Service evaluates submitted state-transition proofs against the operator's configured policy graph before forwarding an HTTP request to an allowed upstream destination. A successful proof is not a guarantee that a request is safe, lawful, accurate, or authorized for every purpose. You are responsible for validating the action, destination, payload, and outcome in your own application. The Service may reject requests, change features, or suspend access to protect the Service, its operator, or other users.

## 2. Acceptable use

You must use the Service only as permitted by applicable law and your authorization from the operator. You must not:

- attempt to bypass, disable, probe, or interfere with policy checks, proof verification, destination restrictions, or other security controls;
- manipulate agent intent, state transitions, proofs, or request payloads to evade an applicable policy or cause an unauthorized action;
- reverse engineer, decompile, or disassemble non-public portions of the hosted Service, except to the extent a restriction is prohibited by applicable law;
- use the Service to transmit unlawful content, compromise systems, access data without authorization, or infringe another person's rights;
- overload, disrupt, or attempt to gain unauthorized access to the Service or its infrastructure; or
- use the Service in a way that violates an upstream provider's terms or your authority to send that provider a request.

You must not submit data you are not authorized to process or disclose. You are responsible for protecting credentials and secrets included in request headers or bodies.

## 3. Rate limits and request constraints

The gateway enforces deployment-configured request-body and upstream-response size limits and an upstream timeout. The current implementation does not provide a built-in per-client request-rate quota. The operator may apply rate limits, quotas, or traffic controls at an ingress, hosting, or upstream-provider layer; comply with any limits communicated to you. Do not evade rate limits or use multiple identities to do so.

## 4. Third-party services

The Service may forward an approved request, including its body and permitted headers, to the upstream destination identified in that request. That destination and its provider are third parties, not controlled by these Terms. Your use of an upstream service is subject to its terms and privacy practices. The gateway operator does not guarantee an upstream service's availability, security, or handling of data.

## 5. Privacy and security

The [Privacy Policy](/privacy) describes how request data and operational logs may be handled. You must not rely on the Service as your sole security control. In particular, a proof over state hashes does not by itself establish that an HTTP request's destination or payload is bound to the proved intent. Do not use the Service as the sole authorization mechanism for safety-critical, financial, or other high-impact actions without independently validating and binding request semantics.

## 6. Disclaimers

TO THE MAXIMUM EXTENT PERMITTED BY LAW, THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE," WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, NON-INFRINGEMENT, ACCURACY, SECURITY, OR UNINTERRUPTED OPERATION. Proof verification and policy checks are not a warranty that an action is safe or that a third-party request will succeed.

## 7. Limitation of liability

TO THE MAXIMUM EXTENT PERMITTED BY LAW, THE SERVICE OPERATOR AND ITS CONTRIBUTORS WILL NOT BE LIABLE FOR INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, EXEMPLARY, OR PUNITIVE DAMAGES, OR FOR LOST PROFITS, DATA, GOODWILL, OR BUSINESS INTERRUPTION, ARISING OUT OF OR RELATED TO THE SERVICE OR THESE TERMS. TO THE MAXIMUM EXTENT PERMITTED BY LAW, THEIR TOTAL LIABILITY FOR ALL CLAIMS RELATING TO THE SERVICE WILL NOT EXCEED THE AMOUNT YOU PAID TO THE OPERATOR FOR THE SERVICE DURING THE TWELVE MONTHS BEFORE THE EVENT GIVING RISE TO THE CLAIM, OR, IF YOU PAID NOTHING, US$100. These limitations do not apply where prohibited by law and do not exclude liability that cannot legally be excluded.

## 8. Changes and contact

The operator may update these Terms by publishing a revised version with an updated effective date. Continued use after the revised Terms take effect constitutes acceptance to the extent permitted by law. Questions about these Terms may be sent to [Proof-of-Intent Gateway Support](mailto:support@proof-of-intent.example). The hosted operator must configure a working support address before public deployment.