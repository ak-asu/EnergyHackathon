import overview from './overview.md?raw'
import architecture from './architecture.md?raw'
import howitworks from './howitworks.md?raw'
import features from './features.md?raw'
import data from './data.md?raw'
import schema from './schema.md?raw'

export const DOCS_NAV = [
  { key: 'overview',     label: 'Overview' },
  { key: 'architecture', label: 'Architecture' },
  { key: 'howitworks',   label: 'How It Works' },
  { key: 'features',     label: 'Features' },
  { key: 'data',         label: 'Data' },
  { key: 'schema',       label: 'Schema' },
]

export const DOCS_PAGES = {
  overview:     { title: 'What is COLLIDE?',        content: overview },
  architecture: { title: 'System Architecture',     content: architecture },
  howitworks:   { title: 'How the Scoring Works',   content: howitworks },
  features:     { title: 'Platform Features',       content: features },
  data:         { title: 'Data Sources & Pipeline', content: data },
  schema:       { title: 'Schema Reference',        content: schema },
}
