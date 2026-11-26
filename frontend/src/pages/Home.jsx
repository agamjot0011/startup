import { Link } from 'react-router-dom'

export default function Home() {
  return (
    <div className="page">
      <h1>Home</h1>
      <div className="home-grid">
        <Link to="/app/p/1/home" className="btn btn-primary">Go to Patient Home</Link>
      </div>
    </div>
  )
}
