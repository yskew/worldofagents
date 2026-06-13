import { useState, useCallback } from 'react';
import { api, decodeSet, type SignalEvent } from '../lib/api';
import SignalsFeed from '../components/SignalsFeed';

export default function Signals() {
  const [events, setEvents] = useState<SignalEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const refresh = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const { sets } = await api.ssfPoll();
      setEvents(Object.entries(sets).map(([jti, token]) => decodeSet(jti, token)));
      setLoaded(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  const ackAll = useCallback(async () => {
    await api.ssfPoll(100, events.map((e) => e.jti));
    setEvents([]);
  }, [events]);

  return (
    <div className="max-w-2xl space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-[Silkscreen] text-coral text-[18px] tracking-[0.14em]">SIGNALS</h1>
          <p className="text-[11px] text-muted mt-1">
            Shared Signals / CAEP risk events emitted to subscribed identity providers.
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={refresh} disabled={loading}
            className="bg-coral text-paper px-3 py-1.5 text-[10px] font-bold tracking-[0.14em] disabled:opacity-50">
            {loading ? 'POLLING…' : 'POLL'}
          </button>
          {events.length > 0 && (
            <button onClick={ackAll}
              className="border border-paper3 text-muted px-3 py-1.5 text-[10px] tracking-[0.14em]">
              ACK ALL
            </button>
          )}
        </div>
      </div>
      {error && <div className="border border-red/40 text-red text-[11px] p-3">{error}</div>}
      {loaded ? <SignalsFeed events={events} /> : (
        <div className="text-[11px] text-dim border border-paper3 p-6 text-center">
          poll the transmitter to load risk signals
        </div>
      )}
    </div>
  );
}
