import { Link } from 'react-router-dom'

export default function Today() {
  return (
    <div className="page">
      <h1>Today&rsquo;s assistant clips</h1>
      <div className="card">
        <h3 className="card-title">Safe notices</h3>
        <p>Read the 5 safety notices from our country.</p>
      </div>
      <div className="card">
        <h3 className="card-title">Loop overview</h3>
        <p>Review open and overdue clinical loops.</p>
        <Link to="/app/assistant" className="btn btn-secondary">View loops</Link>
      </div>
    </div>
  )
}
