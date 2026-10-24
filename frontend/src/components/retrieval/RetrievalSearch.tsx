import { useState } from 'react'
import toast from 'react-hot-toast'
import { Search, Sliders } from 'lucide-react'
import { searchDocuments } from '../../api/client'
import type { ChunkHit, SearchRequest } from '../../types'

export default function RetrievalSearch() {
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(5)
  const [rerank, setRerank] = useState(false)
  const [results, setResults] = useState<ChunkHit[]>([])
  const [searched, setSearched] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSearch = async () => {
    if (!query.trim()) return
    setLoading(true)
    setSearched(false)
    try {
      const req: SearchRequest = { query: query.trim(), top_k: topK, rerank }
      const res = await searchDocuments(req)
      setResults(res.results)
      setSearched(true)
      if (!res.results.length) toast('No results found', { icon: '🔍' })
    } catch {
      toast.error('Search failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fade-up">
      {/* Search box */}
      <div className="search-box">
        <Search size={17} color="var(--text-muted)" />
        <input
          className="search-input"
          placeholder="Search your documents semantically…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
        />
        <button className="btn btn-primary btn-sm" onClick={handleSearch} disabled={loading}>
          {loading ? <div className="spinner" /> : 'Search'}
        </button>
      </div>

      {/* Options */}
      <div className="search-options">
        <label className="search-option-label">
          <Sliders size={13} />
          Top K:
          <input
            type="number"
            min={1} max={50}
            value={topK}
            onChange={e => setTopK(Number(e.target.value))}
          />
        </label>
        <label className="search-option-label">
          <input type="checkbox" checked={rerank} onChange={e => setRerank(e.target.checked)} />
          Enable reranker
        </label>
      </div>

      {/* Results */}
      {searched && (
        <div>
          <h4 style={{ marginBottom: '0.75rem' }}>
            {results.length} result{results.length !== 1 ? 's' : ''} for "{query}"
          </h4>
          {results.map((hit, i) => (
            <div key={hit.chunk_id} className="result-card">
              <div className="result-header">
                <div className="result-doc-info">
                  <div className="result-filename">
                    {(hit.metadata?.filename as string) ?? hit.document_id}
                  </div>
                  <div className="result-ids">
                    doc: {hit.document_id} · chunk: {hit.chunk_id}
                  </div>
                </div>
                <div className="result-score">
                  <span className="score-label">Score</span>
                  <div className="score-bar-wrap">
                    <div className="score-bar-fill" style={{ width: `${hit.score * 100}%` }} />
                  </div>
                  <span className="score-value">{hit.score.toFixed(3)}</span>
                </div>
              </div>
              <div className="result-text">{hit.text}</div>
              <div className="result-meta-row">
                <span className="meta-tag">#{i + 1}</span>
                {hit.metadata?.page != null && (
                  <span className="meta-tag">Page {String(hit.metadata.page)}</span>
                )}
                {hit.metadata?.sequence != null && (
                  <span className="meta-tag">Chunk {String(hit.metadata.sequence)}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {!searched && !loading && (
        <div className="empty-state">
          <div className="empty-state-icon">🔎</div>
          <div className="empty-state-title">Run a semantic search</div>
          <div className="empty-state-desc">
            Type a question or phrase to retrieve the most relevant chunks from your indexed documents using vector similarity.
          </div>
        </div>
      )}
    </div>
  )
}
