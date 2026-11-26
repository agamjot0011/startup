import { Link } from 'react-router-dom'

export default function DoctorHome() {
  return (
    <div className="page">
      <h1>Doctor Home</h1>
      <div className="card">
        <h3 className="card-title">Clinical loop overview</h3>
        <p>Review active, overdue, and recently closed loops for your patients.</p>
        <Link to="/app/doctor" className="btn btn-secondary">View loops</Link>
      </div>
      <div className="card">
        <h3 className="card-title">Patient view</h3>
        <p>View patient timelines, notes, and recent visits.</p>
        <Link to="/app/doctor" className="btn btn-secondary">Open patient</Link>
      </div>
    </div>
  )
}
