import { HORIZON_HEADLINE } from './scenarios';

/** The benchmark population is distinct from the latest stored fleet screening. */
export async function mountPublicSummary(container: HTMLElement): Promise<void> {
  const panel = document.createElement('section');
  panel.className = 'public-result-summary';
  panel.setAttribute('aria-label', 'Measured horizon and stored screening flags');
  const horizon = document.createElement('p');
  horizon.textContent = HORIZON_HEADLINE;
  const flags = document.createElement('p');
  flags.textContent = 'Stored quiet-screening flag counts loading.';
  panel.append(horizon, flags);
  container.prepend(panel);
  try {
    const response = await fetch(`${import.meta.env.BASE_URL}data/conjunctions.json`);
    if (!response.ok) throw new Error('Screening unavailable');
    const data = await response.json();
    if (data.scenario !== 'quiet' || !Array.isArray(data.pairs)) throw new Error('Quiet unavailable');
    const flagged = data.pairs.filter((p: {flag: string}) => ['red', 'yellow'].includes(p.flag));
    const robust = flagged.filter((p: {region: string}) => p.region === 'robust').length;
    const dilution = flagged.filter((p: {region: string}) => p.region === 'dilution').length;
    const share = flagged.length ? (100 * dilution / flagged.length).toFixed(1) : '0.0';
    flags.textContent = `Quiet · ${data.window.start.slice(0, 10)} to ${data.window.end.slice(0, 10)}: ` +
      `${robust} robust-region flagged pairs. Dilution region, low confidence: ${dilution}/${flagged.length} ` +
      `flagged pairs (${share}%). Robust does not certify accurate positions; all probabilities remain indicative.`;
  } catch {
    flags.textContent = 'Stored quiet-screening counts unavailable. No flag count is inferred.';
  }
}
