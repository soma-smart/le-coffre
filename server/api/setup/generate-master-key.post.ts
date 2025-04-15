import { split } from 'shamir-secret-sharing';
import { z } from 'zod'

const generateMasterKeySchema = z.object({
  shares: z.number().min(2).default(5),
  threshold: z.number().min(2).default(3),
}).refine(data => data.shares >= data.threshold, {
  message: "Number of shares must be greater than or equal to the threshold",
})

export default defineEventHandler(async (event) => {
  const result = await readValidatedBody(event, body => generateMasterKeySchema.safeParse(body)) // or `.parse` to directly throw an error

  if (!result.success) {
    throw new Error("Invalid input");
  }

  const randomEntropy = crypto.getRandomValues(new Uint8Array(32));
  const shares = await split(randomEntropy, result.data.shares, result.data.threshold);

  // convert Uint8Array to hex
  const hexShares = shares.map(share => Array.from(share).map(b => b.toString(16).padStart(2, '0')).join(''));

  return {
    shares: hexShares,
  };
});
