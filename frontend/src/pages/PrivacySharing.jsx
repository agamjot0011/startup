import { Link } from 'react-router-dom'

export default function PrivacySharing() {
  return (
    <div className="page">
      <h1>Privacy &amp; sharing</h1>
      <div className="card">
        <h3 className="card-title">Access, consent, and sharing</h3>
        <p>Manage who can access the patient record and with what scopes.</p>
        <Link to="/app/p/1/privacy" className="btn btn-secondary">Manage access</Link>
      </div>
    </div>
  )
}
