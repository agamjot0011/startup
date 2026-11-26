import { Link } from 'react-router-dom'

export default function Help() {
  return (
    <div className="page">
      <h1>Help</h1>
      <div className="card">
        <h3 className="card-title">Support articles</h3>
        <p>Safety notices, clinical loops, and our privacy policy.</p>
        <Link to="/app/p/1/help" className="btn btn-secondary">Browse</Link>
      </div>
    </div>
  )
}
