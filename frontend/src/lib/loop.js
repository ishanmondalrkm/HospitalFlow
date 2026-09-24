// The product loop: monitor, predict, explain, simulate, decide.
export const LOOP = [
  {
    stage: 'Monitor',
    blurb: 'What is happening now',
    live: true,
    pages: [
      { to: '/dashboard', label: 'Overview', ready: true, end: true },
      { to: '/flow', label: 'Hospital flow', ready: true },
      { to: '/history', label: 'Historical trends', ready: true },
    ],
  },
  {
    stage: 'Predict',
    blurb: 'What is likely to happen next',
    pages: [{ to: '/forecast', label: 'Forecast', ready: true }],
  },
  {
    stage: 'Explain',
    blurb: 'Why it is happening',
    pages: [{ to: '/bottlenecks', label: 'Bottlenecks', ready: true }],
  },
  {
    stage: 'Simulate',
    blurb: 'What happens if we act',
    pages: [{ to: '/simulation', label: 'Simulation lab', ready: true }],
  },
  {
    stage: 'Decide',
    blurb: 'Which action to take',
    pages: [{ to: '/insights', label: 'Insights', ready: true }],
  },
]

export const UPCOMING = {
  '/flow': {
    title: 'Hospital flow', stage: 'Monitor', phase: 'Phase 3, dashboard',
    description: 'The hospital drawn as a connected network, so you can watch pressure move from Emergency into the laboratory, beds and discharge.',
  },
  '/forecast': {
    title: 'Forecast', stage: 'Predict', phase: 'Phase 4, forecasting',
    description: 'Waiting-time, queue and pressure forecasts for the next 60 minutes, including when each department is expected to reach critical.',
  },
  '/bottlenecks': {
    title: 'Bottlenecks', stage: 'Explain', phase: 'Phase 5, bottleneck intelligence',
    description: 'The factors behind each bottleneck and the chain of departments it spreads through.',
  },
  '/simulation': {
    title: 'Simulation lab', stage: 'Simulate', phase: 'Phase 6, simulation',
    description: 'Change arrivals, staffing and processing capacity, then compare the projected outcome with the current state before you act.',
  },
  '/insights': {
    title: 'Insights', stage: 'Decide', phase: 'Phase 7, recommendations',
    description: 'Suggested interventions with the projected effect of each, so you can choose with the trade-offs in view.',
  },
}
