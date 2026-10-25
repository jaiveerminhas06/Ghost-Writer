// Labels for the three built-in examples. They are matched BY ORDER to what GET /api/samples returns
// (the API sends the essay texts keyed by long titles; these short tags are for the picker cards).
export const SAMPLE_META = [
  { kind: 'ai', tag: 'AI · Claude', note: 'Model family never seen in training' },
  { kind: 'human', tag: 'Human · student', note: 'An ordinary student essay' },
  { kind: 'human', tag: 'Human · false alarm', note: 'Careful, fluent writing the detector wrongly flags' },
]
