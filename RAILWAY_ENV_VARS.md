# Railway Environment Variables

Copy-paste these into each Railway service's environment variable settings.

---

## Service 1: PostgreSQL

Nothing to configure. Railway auto-provisions this.
Just click "Add" → "Database" → "PostgreSQL".

---

## Service 2: API

Source: GitHub `yskew/worldofagents`, root directory: `/`

Link `DATABASE_URL` from the Postgres plugin via "Add Variable Reference".
Then add these manually:

```
CLERK_SECRET_KEY=sk_test_NecQFIzxAHyadJPAvOUs56c9cCrmSR9eemgtgt1swx
```

```
CLERK_JWKS_URL=https://harmless-chicken-22.clerk.accounts.dev/.well-known/jwks.json
```

```
JWT_ISSUER=worldofagents
```

```
JWT_EXPIRY_SECONDS=3600
```

```
VERIFICATION_PASS_THRESHOLD=0.7
```

```
VERIFICATION_FAIL_THRESHOLD=0.4
```

```
RSA_PRIVATE_KEY_PEM=-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCykpDQLG7mjLG+
Rjm06ARYJ8MCWCxGoZgzEJ/ZKmbeLxOr6GQJ40GVgqvw+zl/pWL5J7GdMfI3C0R7
UsOj7UF6dzSUBF/HFkCBsRubCM86phbMxkDX8Cprt4bwAAZ3JDzaBBFXwmCY5Exq
hbwEL7Shd5H10nIRGYpT/X4cPhKJqnGuAT6QCwrZ9qrnGBORjlz2YNfFIYHpsXpr
OiVXHrmGfs+gP/1dx+kJtbIJFLYkxQQBSZLtT6k1B3VGCKqWGcyRORS9VGLPXAMg
BpQUugYAWWfnqOi4Xi+MaROo82tLdTdYy6ZynOM0kB5+moApl5qOlgO49A2Xlls3
Bt6OW9+3AgMBAAECggEADq3q7TUwRKmKLvvZrVwC7dBCJ2r7vZUPf7S9JZgAiGef
gVrQM0CupbPuBUuEzxzXkjQuIjldEbzn+0J/39wWehL0jCDNhf5eFr5qNSHRqNH6
C9YithDOTx6K7Cdd+ktM6UshgqPxVuaYu/HHolYQzjkxeXi8Qb8zIz//Lu+Q8vOg
FTJE4gFy4rsaoYhQ5yVGg6JLBmVd1nzntWOuSy0bpTAhmrAAthrB4/v80NOZKn9x
eFvRcKjXCfym0kP+m76ywog4rnQDAH7Prk0q4huXSrcbGveJw9c15t0dU7/h/Dx+
5esSTibLWFBER2ZAk1CVkdv1+eap5KVlLgEdciGd+QKBgQDo4XkjtNvjU3VPM9PM
Mn/lgQ5xjtxfGFNCqBmzRwEZigkHOU6jOx+3PBADujrqbuyPkqTSoCX7+2/0IoXM
bgT+macSF0zkz6EqLrpM+35Mygezeq7A7SW/SFJmg7qUrdK9joGevl5kWSHfmLv6
17PoHCNjjnekAVoFs3e23lX+cwKBgQDETOF+Fv50DMEjmTNhLilGCyf7TRa38lbE
YiIHWmpMp07188byY2vRa4SqSYwL81MBiGw7pUvAiP2VNHIqln1b2u/NIUI9vVig
1k4mks9fT+JUmMvlFrMdThXtDfAGQH63cwJQe2N1zfaiDlHvM6G3+eM+BzwrAnMa
Ngr5zT5krQKBgQDTNVsWxTsAS3sDYC/g7JQOZCPjXfwDyx4IQEk+zVD0Brr1cEYf
yMmU98ZWexpf8EZgWFFgLZsFlB8PPhg3NjkVZ+mcgMFea+jxRvv0QctkfX7KiqPf
mbU4bLE/BI29toCBJrPscx9Mx4HvNqiWcfdatdpqupVLi2ZH8WLL2Y4IfQKBgDmD
ENnBYOGdTwTgAMarIJqN8DPXXR2dmcBFxBSFb/lvV1oGBzbC3DbqGl9N1wM1Ug9z
6cn73trVB/6r8/r4RlggJ/vgj6jJDetpflIc1zbkj7obXjmLUgT2+MOQPs+GG9oh
jv8Hd5dvNaA7M9QyO2JMi0CEHCO5vwFh7gtMD8itAoGASF0451913qWd0iTo32id
4kzyVeiSljH5Qlcch1Zm05G9NbwaSFe8uob0rGrf28BLGsV/B8VJTHcBid7QE+oO
bIGDBhs+Rs/l6LouUh3xzRsSnjIetI7yNaVoN8NBEUjfWW4hoyRvZXc3GOXQB7W5
+j180Rx1N+0iSsQ+m1GDjIk=
-----END PRIVATE KEY-----
```

```
RSA_PUBLIC_KEY_PEM=-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAspKQ0Cxu5oyxvkY5tOgE
WCfDAlgsRqGYMxCf2Spm3i8Tq+hkCeNBlYKr8Ps5f6Vi+SexnTHyNwtEe1LDo+1B
enc0lARfxxZAgbEbmwjPOqYWzMZA1/Aqa7eG8AAGdyQ82gQRV8JgmORMaoW8BC+0
oXeR9dJyERmKU/1+HD4SiapxrgE+kAsK2faq5xgTkY5c9mDXxSGB6bF6azolVx65
hn7PoD/9XcfpCbWyCRS2JMUEAUmS7U+pNQd1RgiqlhnMkTkUvVRiz1wDIAaUFLoG
AFln56jouF4vjGkTqPNrS3U3WMumcpzjNJAefpqAKZeajpYDuPQNl5ZbNwbejlvf
twIDAQAB
-----END PUBLIC KEY-----
```

---

## Service 3: Frontend

Source: GitHub `yskew/worldofagents`, root directory: `frontend`
Dockerfile path: `Dockerfile.prod`

These must be set as **build-time variables** (Railway Settings → Build → Build Args):

```
VITE_CLERK_PUBLISHABLE_KEY=pk_test_aGFybWxlc3MtY2hpY2tlbi0yMi5jbGVyay5hY2NvdW50cy5kZXYk
```

```
VITE_API_URL=https://YOUR-API-SERVICE.up.railway.app
```

Replace `YOUR-API-SERVICE` with the actual domain Railway generates for the API service.

---

## Post-Deploy: Clerk Dashboard

Go to https://dashboard.clerk.com → World of Agents app → Settings:

Add your frontend Railway URL to **Allowed Origins / Redirect URLs**:
```
https://YOUR-FRONTEND-SERVICE.up.railway.app
```

---

## Post-Deploy: Seed Data (Optional)

Open the API service's Railway shell and run:
```
python scripts/seed.py
```
