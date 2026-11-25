import { Surface } from '@shared/ui'
import { pct } from '@shared/utils/format'
import type { QuestionStat } from '../../domain/entities/report'

export function QuestionTable({ questions }: { questions: QuestionStat[] }) {
  return (
    <Surface className="overflow-x-auto">
      <h2 className="mb-4 text-lg font-medium">Question by question</h2>
      <table className="w-full text-left text-sm" data-testid="question-table">
        <thead className="text-muted">
          <tr className="border-b border-line">
            <th className="py-2 pr-4 font-medium">Q</th><th className="py-2 pr-4 font-medium">Topic</th>
            <th className="py-2 pr-4 font-medium">Missed</th><th className="py-2 pr-4 font-medium">Key</th>
            <th className="py-2 font-medium">Most common wrong answer</th>
          </tr>
        </thead>
        <tbody>
          {questions.map((q) => (
            <tr key={q.number}>
              <td className="py-2 pr-4 tabular-nums">{q.number}</td>
              <td className="py-2 pr-4">{q.topicTitle ?? 'Not mapped'}</td>
              <td className="py-2 pr-4 tabular-nums">{pct(q.missRate)}</td>
              <td className="py-2 pr-4">{q.correctAnswer ?? 'n/a'}{q.keyFromAi && <span className="text-warn"> (AI, unverified)</span>}</td>
              <td className="py-2 text-muted">{q.commonWrong ?? 'n/a'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Surface>
  )
}
