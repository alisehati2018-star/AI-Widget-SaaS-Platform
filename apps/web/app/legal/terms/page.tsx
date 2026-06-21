import { MarketingFooter, MarketingNav } from "../../../components/marketing";

export const metadata = { title: "Terms of Service — Vitrin" };

export default function TermsPage() {
  return (
    <>
      <MarketingNav />
      <section className="section">
        <div className="container" style={{ maxWidth: 760 }}>
          <h1>Terms of Service</h1>
          <p className="faint">Last updated: 2026-06-21</p>

          <h3>1. Agreement</h3>
          <p>
            These Terms govern your access to and use of the Vitrin platform (&quot;Service&quot;).
            By creating an account or using the Service you agree to these Terms. If you are using
            the Service on behalf of an organization, you accept these Terms for that organization.
          </p>

          <h3>2. Accounts</h3>
          <p>
            You are responsible for safeguarding your credentials and for all activity under your
            account. Notify us promptly of any unauthorized use. You must provide accurate
            information and verify your email address.
          </p>

          <h3>3. Plans &amp; billing</h3>
          <p>
            Paid plans are billed per the pricing shown at checkout. Credits and quotas reset each
            billing period. Manual/invoice payments activate access on confirmation. Fees are
            non-refundable except where required by law.
          </p>

          <h3>4. Acceptable use</h3>
          <p>
            You may not use the Service to violate any law, infringe rights, transmit malware, or
            attempt to breach tenant isolation or access data that is not yours.
          </p>

          <h3>5. Data &amp; tenancy</h3>
          <p>
            Each store is an isolated tenant. You retain ownership of your catalogue and customer
            data. We process it solely to provide the Service, per our Privacy Policy.
          </p>

          <h3>6. Availability &amp; changes</h3>
          <p>
            We aim for high availability but the Service is provided &quot;as is&quot;. We may update
            features and these Terms; material changes will be communicated.
          </p>

          <h3>7. Termination</h3>
          <p>
            You may cancel at any time. We may suspend accounts that violate these Terms. On
            termination you may export your data for a reasonable period.
          </p>

          <h3>8. Contact</h3>
          <p>Questions about these Terms? Reach us via the <a className="grad-text" href="/contact">contact page</a>.</p>
        </div>
      </section>
      <MarketingFooter />
    </>
  );
}
