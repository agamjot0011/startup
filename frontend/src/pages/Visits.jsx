import { Link } from 'react-router-dom'

export default function Visits() {
  return (
    <div className="page">
      <h1>Visits</h1>
      <div className="card">
        <h3 className="card-title">Visit history</h3>
        <p>Historical record of visits.</p>
      </div>
      <div className="card">
        <h3 className="card-title">Upcoming appointments</h3>
        <p>Next appointment with the team.</p>
      </div>
    </div>
  )
}
