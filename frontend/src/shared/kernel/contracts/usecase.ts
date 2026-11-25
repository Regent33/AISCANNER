import type { Result } from '../types/result'

/** One application action. Use cases are the only thing presentation code calls. */
export interface IUseCase<I, O> {
  execute(input: I): Promise<Result<O>>
}
