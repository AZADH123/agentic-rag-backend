import RetrievalSearch from '../components/retrieval/RetrievalSearch'

export default function RetrievalPage() {
  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-header-title">Semantic Search</h1>
          <span className="page-header-desc">
            Direct vector similarity search via <code>/api/v1/retrieval/search</code>
          </span>
        </div>
      </div>
      <div className="page-content">
        <RetrievalSearch />
      </div>
    </>
  )
}
