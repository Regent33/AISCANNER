declare const brand: unique symbol
export type Brand<T, B extends string> = T & { readonly [brand]: B }

export type TestId = Brand<number, 'TestId'>
export type BatchId = Brand<number, 'BatchId'>
export type PaperId = Brand<number, 'PaperId'>
export type ResponseId = Brand<number, 'ResponseId'>

export const asId = <I extends Brand<number, string>>(n: number): I => n as I
