import { Link } from 'react-router-dom'

export default function PatientHome() {
  return (
    <div className="page">
      <h1>Family Home</h1>
      <div className="home-grid">
        <div className="card">
          <h3 className="card-title">Safety first</h3>
          <p>In an emergency, call 999 / go to your nearest A&amp;E.</p>
        </div>
        <div className="card">
          <h3 className="card-title">Today at a glance</h3>
          <p>Read your country&rsquo;s 5 safety notices.</p>
        </div>
        <div className="card">
          <h3 className="card-title">Card inbox</h3>
          <p>Acknowledge and complete assigned cards.</p>
          <Link to="/app/p/1/tasks" className="btn btn-secondary">View tasks</Link>
        </div>
      </div>
    </div>
  )
}
