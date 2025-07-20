import time
from collections import defaultdict
import sympy as sp
import numpy as np
np.set_printoptions(suppress=True,linewidth=1000000)

class Action:
    S = [0.50, 0.45, 0.45, 0.40, 0.40, 0.40, 0.35, 0.35, 0.35, 0.35,
         0.30, 0.30, 0.30, 0.30, 0.30, 0.30, 0.30, 0.30, 0.30, 0.30, ]

    def __init__(self, target_level, protect_level, bless, bonus_rate, enhance_cost=1, protect_cost=100):
        self.target_level = target_level
        protect_level = max(2, protect_level)
        self.protect_level = protect_level
        self.enable_protect = self.protect_level < self.target_level
        self.bless = bless
        self.bonus_rate = bonus_rate
        self.P = np.zeros((target_level + 1, target_level + 1))
        self.H = np.zeros((target_level + 1, target_level + 1))
        self.H_exp = np.zeros((target_level + 1, target_level + 1))
        self.H_protect = np.zeros((target_level + 1, target_level + 1))
        self.enhance_cost = enhance_cost
        self.protect_cost = protect_cost
        for i in range(min(target_level, protect_level)):
            self.P[i][0] = 1 - Action.S[i] * (1 + bonus_rate)
            self.H[i][0] = enhance_cost
            self.H_exp[i, :] = 1.4 * (1 + i)
            self.H_exp[i][0] = 1.4 * (1 + i)
            if i + 1 < target_level:
                self.P[i][i + 1] = Action.S[i] * (1 + bonus_rate) * (1 - bless)
                self.P[i][i + 2] = Action.S[i] * (1 + bonus_rate) * bless
                self.H[i][i + 1] = enhance_cost
                self.H[i][i + 2] = enhance_cost
            else:
                self.P[i][i + 1] = Action.S[i] * (1 + bonus_rate)
                self.H[i][i + 1] = enhance_cost
        for i in range(protect_level, target_level):
            self.P[i][i - 1] = 1 - Action.S[i] * (1 + bonus_rate)
            self.H[i][i - 1] = enhance_cost + protect_cost
            self.H_protect[i][i - 1] = 1
            self.H_exp[i, :] = 1.4 * (1 + i)
            self.H_exp[i][i - 1] = 0.14 * (1 + i)
            if i + 1 < target_level:
                self.P[i][i + 1] = Action.S[i] * (1 + bonus_rate) * (1 - bless)
                self.P[i][i + 2] = Action.S[i] * (1 + bonus_rate) * bless
                self.H[i][i + 1] = enhance_cost
                self.H[i][i + 2] = enhance_cost
            else:
                self.P[i][i + 1] = Action.S[i] * (1 + bonus_rate)
                self.H[i][i + 1] = enhance_cost
        self.P[target_level][target_level] = 1.0
        self.Q = self.P[:-1, :-1]
        self.R = self.P[:-1, -1]
        self.N = np.linalg.inv(np.eye(target_level) - self.Q)

    def __str__(self, lean=True):
        if lean:
            return f'T+{self.target_level} P{f"+{self.protect_level}" if self.enable_protect else " X"}'
        return f'Target:+{self.target_level}, Protect:{self.protect_level if self.enable_protect else "None"}, Enhance Cost={self.enhance_cost}, Protect Cost={self.protect_cost}'

    @property
    def expected_steps(self):
        u0 = np.zeros(self.target_level)
        u0[0] = 1.0
        return u0 @ self.N @ np.ones(self.target_level)

    @property
    def expected_cost(self):
        u0 = np.zeros(self.target_level)
        u0[0] = 1.0
        return u0 @ self.N @ (self.P[:-1, :] * self.H[:-1, :]) @ np.ones(self.target_level + 1)

    @property
    def expected_protect(self):
        if not self.enable_protect:
            return 0.0
        u0 = np.zeros(self.target_level)
        u0[0] = 1.0
        return u0 @ self.N @ (self.P[:-1, :] * self.H_protect[:-1, :]) @ np.ones(self.target_level + 1)

    @property
    def expected_exp(self):
        u0 = np.zeros(self.target_level)
        u0[0] = 1.0
        return u0 @ self.N @ (self.P[:-1, :] * self.H_exp[:-1, :]) @ np.ones(self.target_level + 1)

    def cost_cdf(self, steps, tol=1e-10, method='DP', compute_phi_method='CRAMER', debug=False):
        """
        method : "DP" = Dynamic Programming
                 "CF" = Characteristic Function
        """

        def debug_print(*args, **kwargs):
            if debug:
                print(method + (compute_phi_method if method == 'CFsym' else ''), str(self), f'{time.time():.3f}', *args, **kwargs)

        if method not in ('DP', 'CFsym','CFnum'):
            raise ValueError('method must be DP or CFsym or CFnum')
        if method == 'DP':
            debug_print('initialize')
            a = self.enhance_cost
            b = self.enhance_cost + self.protect_cost
            distribution = defaultdict(float)
            f = np.zeros((steps + 1, self.target_level + 1))
            f[0][self.target_level] = 1.0
            debug_print("start")
            progress = 0
            total_prob = 0.0
            for step in range(1, steps + 1):  # step = k1+k2
                for k1 in reversed(range(step + 1)):  # k1
                    f[k1] = [
                        sum(
                            self.P[i][j] * (
                                f[k1 - 1][j] if (self.H[i][j] == a and k1 > 0) else (f[k1][j] if (self.H[i][j] == b and k1 < step) else 0.0)
                            )
                            for j in range(self.target_level + 1)
                        )
                        for i in range(self.target_level + 1)
                    ]
                    if f[k1][0]:
                        distribution[k1 * a + (step - k1) * b] += f[k1, 0]
                    if k1 + 1 < steps and sum(f[k1]) < sum(f[k1 + 1]) and sum(f[k1]) <= tol:
                        f[k1] = [0.0 for _ in range(self.target_level + 1)]
                        break
                    if not any(f[k1]):
                        break
                if step / steps >= progress / 100:
                    debug_print(f'progress: {step / steps * 100:.0f}%')
                    progress += 10
                total_prob += np.sum(f[:, 0])
            debug_print("total probability:", total_prob)
            xs = np.array([0.0] + sorted(filter(lambda i: i < (steps + 1) * a, distribution.keys())))
            ys = np.zeros(len(xs))
            for i, x in enumerate(xs):
                ys[i] = distribution[x] + (ys[i - 1] if i > 0 else 0.0)
            debug_print("Done")
            return xs, ys
        elif method == 'CFsym':
            debug_print("initialize")
            t = sp.Symbol('t')
            A = sp.zeros(self.target_level, self.target_level)
            b = sp.zeros(self.target_level, 1)
            for i in range(self.target_level):
                for j in range(self.target_level):
                    A[i, j] = self.P[i, j] * sp.exp(1j * t * self.H[i, j])
                b[i, 0] = self.P[i, self.target_level] * sp.exp(1j * t * self.H[i, self.target_level])
            debug_print('compute phi')
            if compute_phi_method == 'IM':
                phi = (sp.Matrix.inv(sp.eye(self.target_level) - A) * b)[0]
            else:
                phi = (sp.eye(self.target_level) - A).solve(b, method=compute_phi_method)[0]
            phi.simplify()
            debug_print('phi(t) =', phi)
            phi = sp.lambdify(t, phi, modules='numpy')
            end = int(steps * self.enhance_cost)
            step = 1
            samples_N = 2 ** max(16, 2 + int(np.ceil(np.log2((end + 1024)))))

            j = np.arange(samples_N)
            t = 2 * np.pi * j / samples_N
            debug_print('compute samples & IFFT, N =', samples_N)
            phi_samples = phi(t)
            pmf = np.fft.ifft(np.conj(phi_samples)).real
            # pmf = np.clip(pmf, 0, None)
            pmf[np.abs(pmf) <= tol] = 0
            total_prob = np.sum(pmf)
            debug_print('total probability:', total_prob)
            if total_prob <= 0:
                raise ValueError('Failed: Negative Probability')
            pmf /= total_prob
            cdf_full = np.cumsum(pmf)

            ys = cdf_full[:end + 1]
            xs = np.arange(end + 1)
            return xs, ys
        elif method == 'CFnum':
            end = int(steps * self.enhance_cost)
            samples_N = 2 ** max(12, 2 + int(np.ceil(np.log2((end + 1024)))))
            debug_print('samples N =', samples_N)
            j = np.arange(0,samples_N)
            t = 2 * np.pi * j / samples_N
            debug_print('initialize')
            A = self.P[:-1, :-1] * np.exp(1j * t[:, None,None] * self.H[:-1, :-1])
            b = (self.P[:-1,-1] * np.exp(1j * t[:, np.newaxis] * self.H[:-1, -1]))[..., np.newaxis]
            I = np.eye(self.target_level)
            debug_print('compute phi')
            print((I-A)[samples_N//3])
            print(np.linalg.inv(I-A)[samples_N//3])
            phi_samples = np.linalg.solve((I-A),b)[:,0,0]
            debug_print('compute IFFT')
            pmf = np.fft.ifft(np.conj(phi_samples)).real
            # pmf = np.clip(pmf, 0, None)
            pmf[np.abs(pmf) <= tol] = 0
            total_prob = np.sum(pmf)
            debug_print('total probability:', total_prob)
            if total_prob <= 0:
                raise ValueError('Failed: Negative Probability')
            pmf /= total_prob
            cdf_full = np.cumsum(pmf)

            ys = cdf_full[:end + 1]
            xs = np.arange(0,end + 1)
            return xs, ys
