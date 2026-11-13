import { siteName, usePageTitle } from "../../app/usePageTitle";
import "./legal.css";

export function LegalPage() {
  usePageTitle("Legal");

  return <article className="utility-page legal-page" aria-labelledby="legal-heading">
    <header>
      <p className="eyebrow">Public educational demo</p>
      <h1 className="page-title" id="legal-heading">Legal</h1>
    </header>
    <section aria-labelledby="legal-license">
      <h2 id="legal-license">License and warranties</h2>
      <p>{siteName} is distributed under the{" "}
        <a href="https://github.com/serh11chyrva/fastapi-blog-example/blob/main/LICENSE"
          target="_blank" rel="noopener noreferrer">MIT License</a>.
        The software and this demo are provided &quot;as is&quot;, without warranties, to the extent permitted by law.
        We do not guarantee correct operation, availability, data preservation, security, or confidentiality.
        Do not submit sensitive or confidential information.</p>
    </section>
    <section aria-labelledby="legal-data">
      <h2 id="legal-data">Data and third-party services</h2>
      <p>The demo uses a session cookie for sign-in and stores database records in{" "}
        <a href="https://www.mongodb.com/legal/privacy" target="_blank" rel="noopener noreferrer">MongoDB Atlas</a>.
        Public profiles and public content are visible to other visitors. Embedded players and external preview images
        may connect to third-party providers as content comes into view. These providers may receive your IP address
        and browser information and use their own cookies; their own terms and privacy practices apply.</p>
    </section>
    <section aria-labelledby="legal-forks">
      <h2 id="legal-forks">Forks and other deployments</h2>
      <p>Independent forks, modified versions, and other deployments may change how data is collected, stored, shared,
        or processed. The original project maintainers do not control those versions or their operators&apos; practices
        and cannot guarantee how they handle data.</p>
    </section>
    <p className="legal-note">Nothing in this notice limits rights or obligations that cannot be excluded under applicable law.</p>
  </article>;
}
