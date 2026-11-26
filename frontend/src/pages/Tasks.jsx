import { Link } from 'react-router-dom'

export default function Tasks() {
  return (
    <div className="page">
      <h1>Today&rsquo;s tasks</h1>
      <div className="card">
        <h3 className="card-title">Safety notices</h3>
        <p>Read the 5 safety notices from our country.</p>
      </div>
      <div className="card">
        <h3 className="card-title">Active cards</h3>
        <p>Acknowledge and complete assigned cards.</p>
        <Link to="/app/p/1/tasks" className="btn btn-secondary">View cards</Link>
      </div>
    </div>
  )
}
