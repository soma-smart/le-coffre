import process from 'node:process'
import { consola } from 'consola'

// From consola docs, available log levels:
// 0: Fatal and Error
// 1: Warnings
// 2: Normal logs
// 3: Informational logs, success, fail, ready, start, ...
// 4: Debug logs
// 5: Trace logs
//   - 999: Silent
//     + 999: Verbose logs

export default defineNitroPlugin((_nitroApp) => {
  consola.level = 3
  // if ENV=DEV, set to 4 (debug)
  if (process.env.ENV === 'DEV') {
    consola.level = 4
  }
})
