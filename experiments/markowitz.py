#    Copyright 2023 Stanford University Convex Optimization Group
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.from dataclasses import dataclass
from dataclasses import dataclass

import numpy as np
import cvxpy as cp


@dataclass
class Data:
    w_prev: np.ndarray  # (n_assets,) array of previous asset weights
    idio_mean: np.ndarray  # (n_assets,) array of idiosyncratic mean returns
    factor_mean: np.ndarray  # (n_factors,) array of factor mean returns
    risk_free: float  # risk-free rate
    factor_covariance_chol: np.ndarray  # (n_factors, n_factors) covariance matrix of factor returns
    idio_volas: np.ndarray  # (n_assets,) array of idiosyncratic volatilities
    F: np.ndarray  # (n_assets, n_factors) array of factor exposures
    kappa_short: np.ndarray  # (n_assets,) array of shorting cost
    kappa_borrow: float  # borrowing cost
    kappa_spread: np.ndarray  # (n_assets,) array of bid-ask spreads
    kappa_impact: np.ndarray  # (n_assets,) array of market impact costs

    @property
    def n_assets(self) -> int:
        return self.w_prev.size

    @property
    def volas(self) -> np.ndarray:
        return self.idio_volas + np.linalg.norm(
            self.F @ self.factor_covariance_chol, axis=1
        )


@dataclass
class Parameters:
    w_min: np.ndarray  # (n_assets,) array of lower bounds on asset weights
    w_max: np.ndarray  # (n_assets,) array of upper bounds on asset weights
    c_min: float  # lower bound on cash weight
    c_max: float  # upper bound on cash weight
    z_min: np.ndarray  # (n_assets,) array of lower bounds on trades
    z_max: np.ndarray  # (n_assets,) array of upper bounds on trades
    T_tar: float  # turnover target
    L_tar: float  # leverage target
    risk_target: float
    rho_mean: np.ndarray  # (n_assets,) array of mean returns for rho
    rho_covariance: float  # uncertainty in covariance matrix
    gamma_hold: float  # holding cost
    gamma_trade: float  # trading cost
    gamma_turn: float  # turnover cost
    gamma_risk: float  # risk cost
    gamma_leverage: float  # leverage gamma


@dataclass
class HyperParameters:
    gamma_hold: float
    gamma_trade: float
    gamma_turn: float
    gamma_leverage: float
    gamma_risk: float


@dataclass
class Targets:
    T_target: float
    L_target: float
    risk_target: float


@dataclass
class Limits:
    T_max: float
    L_max: float
    risk_max: float


def markowitz(
    data: Data,
    param: Parameters,
) -> tuple[np.ndarray, float, cp.Problem]:
    """
    Markowitz portfolio optimization.
    This function contains the code listing for the accompanying paper.
    """

    w, c = cp.Variable(data.n_assets), cp.Variable()

    z = w - data.w_prev
    T = cp.norm1(z) / 2
    L = cp.norm1(w)

    # worst-case (robust) return
    factor_return = (data.F @ data.factor_mean).T @ w
    idio_return = data.idio_mean @ w
    mean_return = factor_return + idio_return + data.risk_free * c
    return_uncertainty = param.rho_mean @ cp.abs(w)
    return_wc = mean_return - return_uncertainty

    # worst-case (robust) risk
    factor_risk = cp.norm2((data.F @ data.factor_covariance_chol).T @ w)
    idio_risk = cp.norm2(cp.multiply(data.idio_volas, w))
    risk = cp.norm2(cp.hstack([factor_risk, idio_risk]))
    risk_uncertainty = param.rho_covariance**0.5 * data.volas @ cp.abs(w)
    risk_wc = cp.norm2(cp.hstack([risk, risk_uncertainty]))

    asset_holding_cost = data.kappa_short @ cp.pos(-w)
    cash_holding_cost = data.kappa_borrow * cp.pos(-c)
    holding_cost = asset_holding_cost + cash_holding_cost

    spread_cost = data.kappa_spread @ cp.abs(z)
    impact_cost = data.kappa_impact @ cp.power(cp.abs(z), 3 / 2)
    trading_cost = spread_cost + impact_cost

    objective = (
        return_wc - param.gamma_hold * holding_cost - param.gamma_trade * trading_cost
    )

    constraints = [
        cp.sum(w) + c == 1,
        param.w_min <= w,
        w <= param.w_max,
        L <= param.L_tar,
        param.c_min <= c,
        c <= param.c_max,
        param.z_min <= z,
        z <= param.z_max,
        T <= param.T_tar,
        risk_wc <= param.risk_target,
    ]

    objective = (
        return_wc
        - param.gamma_risk * cp.pos(risk_wc - param.risk_target)
        - param.gamma_hold * holding_cost
        - param.gamma_trade * trading_cost
        - param.gamma_turn * cp.pos(T - param.T_max)
        - param.gamma_leverage * cp.pos(L - param.L_max)
    )

    problem = cp.Problem(cp.Maximize(objective), constraints)

    try:
        problem.solve(solver="MOSEK", verbose=False)
    except cp.SolverError:
        print("SolverError")
        print(problem.status)

    try:
        assert problem.status in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE}, problem.status
    except AssertionError:
        print("Problem status: ", problem.status)

        return data.w_prev, data.c_prev, problem, False

    return w.value, c.value, problem, True


if __name__ == "__main__":
    # Create empty data and parameters objects to check types and shapes,
    # will be replaced by example data

    n_assets = 10
    data = Data(
        w_prev=np.ones(n_assets) / n_assets,
        idio_mean=np.zeros(n_assets),
        factor_mean=np.zeros(n_assets),
        risk_free=0.0,
        factor_covariance_chol=np.zeros((n_assets, n_assets)),
        idio_volas=np.zeros(n_assets),
        F=np.zeros((n_assets, n_assets)),
        kappa_short=np.zeros(n_assets),
        kappa_borrow=0.0,
        kappa_spread=np.zeros(n_assets),
        kappa_impact=np.zeros(n_assets),
    )

    param = Parameters(
        w_min=np.zeros(n_assets),
        w_max=np.ones(n_assets),
        c_min=0.0,
        c_max=1.0,
        z_min=-np.ones(n_assets),
        z_max=np.ones(n_assets),
        T_tar=1.0,
        L_tar=1.0,
        rho_mean=np.zeros(n_assets),
        rho_covariance=0.0,
        gamma_hold=0.0,
        gamma_trade=0.0,
        gamma_turn=0.0,
        gamma_risk=0.0,
        risk_target=0.0,
    )

    w, c, _ = markowitz(data, param)
    print(w, c)