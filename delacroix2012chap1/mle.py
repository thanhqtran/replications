# estimate parameters eta, phi, theta, eta using MLE
# data is the dataframe data_est
# equations that use the parameters are w_, e_, n_
# y is gdp, n is fertility, e is education, v is productivity

# some libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from sklearn.metrics import r2_score  #to estimate fitness

# import the cleaned dataset
dat = pd.read_csv('dataset.csv')
data = pd.DataFrame(dat)

# helper functions:
# equations to estimate the parameters
# w = y/(1-phi*n)
# e = (eta*phi*w - theta)/(1-eta) if w > theta/(eta*phi) else 0
# n = (1-eta)*gamma*w/((1+gamma)*(phi*w - theta)) if w > theta/(eta*phi) else gamma/(phi*(1+gamma))
# observed variables: y, n, e+theta
# latent variables: w, e
# parameters to estimate: eta, phi, theta, gamma
# assume that residuals are normally distributed

# model's implied values
def compute_model_values(y, n, eta, phi, theta, gamma):
    w = y / (1 - phi * n)
    w_thresh = theta / (eta * phi)

    e = np.where(w > w_thresh, (eta * phi * w - theta) / (1 - eta), 0.0)
    e_plus_theta = e + theta

    n_model = np.where(
        w > w_thresh,
        (1 - eta) * gamma * w / ((1 + gamma) * (phi * w - theta)),
        gamma / (phi * (1 + gamma))
    )

    return w, e_plus_theta, n_model

# log-likelihood function
def neg_log_likelihood(params, y_data, n_data, e_plus_theta_data):
    eta, phi, theta, gamma, log_sigma_n, log_sigma_e = params
    sigma_n = np.exp(log_sigma_n)
    sigma_e = np.exp(log_sigma_e)

    # Boundary check
    if not (0 < eta < 1 and 0 < phi < 1 and theta > 0 and gamma > 0):
        return 1e10  # large penalty for infeasible parameters

    try:
        _, e_plus_theta_model, n_model = compute_model_values(y_data, n_data, eta, phi, theta, gamma)
    except:
        return 1e10  # handle potential division by zero

    # calculate the residual fromm data to model
    res_n = n_data - n_model
    res_e = e_plus_theta_data - e_plus_theta_model
    
    # f(x) = 1/(sqrt{2 \pi \sigma^2} \exp( - x^2/(2\sigma^2))
    # \log f(x) = -1/2 * (\log(2\pi\sigma^2) + x^2/\sigma^2)
    ll = -0.5 * np.sum(np.log(2 * np.pi * sigma_n ** 2) + (res_n ** 2) / sigma_n ** 2) \
         -0.5 * np.sum(np.log(2 * np.pi * sigma_e ** 2) + (res_e ** 2) / sigma_e ** 2)
    
    return -ll  # minimize negative log-likelihood

# perform mle
y_data, n_data, e_plus_theta_data = data['y'].values, data['n'].values, data['e+theta'].values
initial_guess = [0.5, 0.03, 60, 0.1, np.log(0.1), np.log(0.1)]
result = minimize(
    neg_log_likelihood, 
    initial_guess, 
    args=(y_data, n_data, e_plus_theta_data), 
    method='L-BFGS-B',
    options={'disp': True}
)
estimated_params = result.x
print("Estimated Parameters:")
print(f"eta: {estimated_params[0]:.4f}, phi: {estimated_params[1]:.4f}, theta: {estimated_params[2]:.4f}, gamma: {estimated_params[3]:.4f}")

# store estimated parameters
estimated_params = result.x
eta, phi, theta, gamma, log_sigma_n, log_sigma_e = estimated_params
# Compute the model-implied latent variables:
w_hat, e_plus_theta_hat, n_hat = compute_model_values(y_data, n_data, eta, phi, theta, gamma)
e_hat = e_plus_theta_hat - theta

# Compute R^2 scores
#r2_score = lambda true, pred: 1 - np.sum((true - pred) ** 2) / np.sum((true - np.mean(true)) ** 2)
r2_n = r2_score(n_data, n_hat)
r2_e = r2_score(e_plus_theta_data - theta, e_hat)

print(f"R² for n: {r2_n:.4f}")
print(f"R² for e: {r2_e:.4f}")

#=============================================
# --- Robustness check using other algorithms
# --- OPTIONAL ------------------------------
# I find this method 'L-BFGS-B' resembles the closest to the chapter

# Test different optimization methods
np.set_printoptions(suppress=True)

methods = ['Powell', 'Nelder-Mead', 'L-BFGS-B']

# initialize a dictionary to store results from each method
results = {}

for method in methods:
    print(f"\n--- Method: {method} ---")
    result = minimize(
        neg_log_likelihood,
        initial_guess,
        args=(y_data, n_data, e_plus_theta_data),
        method=method,
        options={'disp': True, 'maxiter': 100000}
    )
    results[method] = result
    print("Estimated parameters:", result.x)

# model selection crieterion
import numpy as np
from sklearn.metrics import r2_score, mean_squared_error

def evaluate_model(params, y_data, n_data, e_plus_theta_data):
    eta, phi, theta, gamma = params[:4]
    log_sigma_n, log_sigma_e = params[4], params[5]
    sigma_n = np.exp(log_sigma_n)
    sigma_e = np.exp(log_sigma_e)
    k = 6  # number of parameters
    n_obs = len(y_data)

    # Get model predictions
    w_hat, e_plus_theta_hat, n_hat = compute_model_values(y_data, n_data, eta, phi, theta, gamma)

    # Compute residuals
    res_n = n_data - n_hat
    res_e = e_plus_theta_data - e_plus_theta_hat

    # Log-likelihood
    ll = -0.5 * np.sum(np.log(2 * np.pi * sigma_n ** 2) + (res_n ** 2) / sigma_n ** 2) \
         -0.5 * np.sum(np.log(2 * np.pi * sigma_e ** 2) + (res_e ** 2) / sigma_e ** 2)

    # AIC and BIC
    aic = 2 * k - 2 * ll
    bic = k * np.log(n_obs) - 2 * ll

    # R² scores and RMSE
    r2_n = r2_score(n_data, n_hat)
    r2_e = r2_score(e_plus_theta_data, e_plus_theta_hat)

    rmse_n = np.sqrt(mean_squared_error(n_data, n_hat))
    rmse_e = np.sqrt(mean_squared_error(e_plus_theta_data, e_plus_theta_hat))

    return {
        'log_likelihood': ll,
        'AIC': aic,
        'BIC': bic,
        'R2_n': r2_n,
        'R2_e+θ': r2_e,
        'RMSE_n': rmse_n,
        'RMSE_e+θ': rmse_e
    }

# Evaluate the model with the estimated parameters
model1 = results['L-BFGS-B']
model2 = results['Powell']
model3 = results['Nelder-Mead']
evaluation1 = evaluate_model(model1.x, y_data, n_data, e_plus_theta_data)
evaluation2 = evaluate_model(model2.x, y_data, n_data, e_plus_theta_data)
evaluation3 = evaluate_model(model3.x, y_data, n_data, e_plus_theta_data)
# Print evaluation results
print("\n--- Evaluation Results for L-BFGS-B ---")
for key, value in evaluation1.items():
    print(f"{key}: {value:.4f}")
print("\n--- Evaluation Results for Powell ---")
for key, value in evaluation2.items():
    print(f"{key}: {value:.4f}")
print("\n--- Evaluation Results for Nelder-Mead ---")
for key, value in evaluation3.items():
    print(f"{key}: {value:.4f}")
# Compare the evaluations
evaluations = {
    'L-BFGS-B': evaluation1,
    'Powell': evaluation2,
    'Nelder-Mead': evaluation3
}
