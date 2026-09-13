import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useEvalReport, useVersion } from "../api/queries";
import { ArchitectureDiagram } from "../components/ArchitectureDiagram";
import { ErrorState } from "../components/StateMessage";
import { describeError } from "../lib/errorMessage";
import styles from "./UnderTheHood.module.css";

function ciLabel(mean: number, low: number, high: number): string {
  return `${mean.toFixed(3)} [${low.toFixed(3)}, ${high.toFixed(3)}]`;
}

export default function UnderTheHood() {
  const version = useVersion();
  const report = useEvalReport();

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Under the hood</h1>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Architecture</h2>
        <div className={styles.diagramWrap}>
          <ArchitectureDiagram />
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Model and bundle versions</h2>
        {version.isPending && <p className={styles.note}>Loading…</p>}
        {version.isError && (
          <ErrorState
            message={describeError("version info", version.error)}
            onRetry={() => version.refetch()}
          />
        )}
        {version.isSuccess && (
          <div className={styles.versionGrid}>
            <div className={styles.versionCard}>
              <div className={styles.versionLabel}>Bundle version</div>
              <div className={styles.versionValue}>{version.data.bundle_version}</div>
            </div>
            <div className={styles.versionCard}>
              <div className={styles.versionLabel}>Catalog size</div>
              <div className={styles.versionValue}>{version.data.n_items} products</div>
            </div>
            <div className={styles.versionCard}>
              <div className={styles.versionLabel}>Default weights</div>
              <div className={styles.versionValue}>
                image {version.data.default_weights.image} · text {version.data.default_weights.text}{" "}
                · meta {version.data.default_weights.meta}
              </div>
            </div>
            {Object.entries(version.data.models).map(([key, value]) => (
              <div className={styles.versionCard} key={key}>
                <div className={styles.versionLabel}>{key}</div>
                <div className={styles.versionValue}>{value}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      {report.isError && (
        <ErrorState
          message={describeError("the evaluation report", report.error)}
          onRetry={() => report.refetch()}
        />
      )}

      {report.isPending && !report.isError && <p className={styles.note}>Loading evaluation report…</p>}

      {report.isSuccess && (
        <>
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>
              Evaluation ({report.data.n_queries} labeled queries, k={report.data.k})
            </h2>
            <div className={styles.tableWrap}>
              <table>
                <thead>
                  <tr>
                    <th>Method</th>
                    <th>NDCG@5 [95% CI]</th>
                    <th>P@5 [95% CI]</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(report.data.methods).map(([method, metric]) => (
                    <tr key={method}>
                      <td>{method}</td>
                      <td>
                        {ciLabel(
                          metric.ndcg_at_5.mean,
                          metric.ndcg_at_5.ci_low,
                          metric.ndcg_at_5.ci_high,
                        )}
                      </td>
                      <td>
                        {ciLabel(metric.p_at_5.mean, metric.p_at_5.ci_low, metric.p_at_5.ci_high)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className={styles.note}>{report.data.fused_vs_baseline.note}</p>
          </section>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Hubness — top recommended-everywhere products</h2>
            <p className={styles.note}>
              Mean in-degree {report.data.proxies.hubness.mean_indegree.toFixed(2)}, skewness{" "}
              {report.data.proxies.hubness.skewness.toFixed(2)} (full 472-product catalog). The chart
              below shows the five products that show up most often in other products&apos; top-5 lists.
            </p>
            <div className={styles.chartWrap}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={report.data.proxies.hubness.top_hubs.map((h) => ({
                    title: h.title.length > 28 ? `${h.title.slice(0, 28)}…` : h.title,
                    count: h.count,
                  }))}
                  layout="vertical"
                  margin={{ left: 8, right: 16, top: 8, bottom: 8 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-accent-silver)" opacity={0.25} />
                  <XAxis type="number" stroke="var(--color-surface)" fontSize={11} />
                  <YAxis
                    type="category"
                    dataKey="title"
                    width={160}
                    stroke="var(--color-surface)"
                    fontSize={11}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "var(--color-ground)",
                      border: "1px solid var(--color-accent-gold)",
                      color: "var(--color-surface)",
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="count" fill="var(--color-accent-gold)" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Failure cases</h2>
            <p className={styles.note}>The five lowest-NDCG queries under the tuned model.</p>
            <div className={styles.failureGrid}>
              {report.data.failure_cases.map((fc) => (
                <div className={styles.failureCard} key={fc.query_sku}>
                  <div className={styles.failureQuery}>{fc.query_title}</div>
                  <div className={styles.failureNdcg}>NDCG@5 = {fc.ndcg_at_5.toFixed(3)}</div>
                  <ul className={styles.failureList}>
                    {fc.top5.map((item) => (
                      <li key={item.sku}>
                        {item.title} (label {item.label})
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Methodology notes</h2>
            {report.data.methodology_notes.map((note) => (
              <p className={styles.note} key={note.slice(0, 40)}>
                {note}
              </p>
            ))}
          </section>
        </>
      )}
    </div>
  );
}
