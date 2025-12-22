/**
 * Analytics Module
 *
 * Exports for HEART metrics tracking and GSM framework.
 */

// HeartAggregator - Event batching and aggregation
export {
  HeartAggregator,
  type QueuedEvent,
  type SessionContext,
  type HeartAggregatorConfig,
  type AggregatorStats,
} from "./HeartAggregator";

// GSM Framework re-exports
export * from "./gsm";
