import { FormProvider, useForm } from 'react-hook-form'
import { zfd } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api } from '../api'

const reportSchema = z.object({
  description: z.string().min(1, 'Description is required'),
  channel: z.string().optional(),
})

export default function ReportProblem() {
  const methods = useForm({ resolver: zfd.zodResolver(reportSchema) })
  const [msg, setMsg] = 'state'

  async function onSubmit(data) {
    try {
      const body = await api.post('/v1/patients/synthetic/problem-reports', {
        description: data.description,
        channel: data.channel,
      })
      setMsg('Reported: ' + body.status)
      methods.reset()
    } catch (e) {
      setMsg(e.message)
    }
  }

  return (
    <div className="page">
      <h1>Report a problem</h1>
      <FormProvider {...methods}>
        <form onSubmit={methods.handleSubmit(onSubmit)}>
          <input name="description" placeholder="What happened?" />
          <select name="channel">
            <option value="front_desk">Front desk</option>
            <option value="doctor">Doctor</option>
          </select>
          <button type="submit" className="btn btn-primary">Submit report</button>
        </form>
        {msg && <p className="form-success">{msg}</p>}
      </FormProvider>
    </div>
  )
}
