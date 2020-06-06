# RandomForestClassifier
import numpy as np
from textClassifier.Svm import functions
import warnings

## Sklearn Libraries
from sklearn.preprocessing import label_binarize
from sklearn.model_selection import train_test_split
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import f1_score, confusion_matrix, roc_curve,  \
            classification_report, recall_score
from sklearn.ensemble import RandomForestClassifier
from sklearn import preprocessing
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import make_scorer

# Define random state
random_state = 2020
np.random.seed(random_state)

# x = np.load('../data/input/ga_sample_vector.npy')
# y = np.load('../data/input/label.npy')
# x_train, x_test, y_train, y_test = train_test_split(x, y, train_size=0.75, random_state=1, stratify=y)

sample_vec = np.load('../data/input/doc2vec_sample_vector.npy')
label_list = np.load('../data/input/label.npy')
label_list = list(label_list)

# split sample into healthy ones and ill ones
healthy, ill = functions.split_sample(sample_vec, label_list)
x_train, y_train, x_test, y_test = functions.get_sets(healthy, ill)


# A. Create ensembel class
class Create_ensemble(object):
    def __init__(self, n_splits, base_models):
        self.n_splits = n_splits
        self.base_models = base_models

    def predict(self, X, y, T):
        X = np.array(X)
        y = np.array(y)
        T = np.array(T)
        no_class = len(np.unique(y))

        folds = list(StratifiedKFold(n_splits=self.n_splits, shuffle=True,
                                     random_state=random_state).split(X, y))

        train_proba = np.zeros((X.shape[0], no_class))
        test_proba = np.zeros((T.shape[0], no_class))

        train_pred = np.zeros((X.shape[0], len(self.base_models)))
        test_pred = np.zeros((T.shape[0], len(self.base_models) * self.n_splits))
        f1_scores = np.zeros((len(self.base_models), self.n_splits))
        recall_scores = np.zeros((len(self.base_models), self.n_splits))

        test_col = 0
        for i, clf in enumerate(self.base_models):

            for j, (train_idx, valid_idx) in enumerate(folds):
                X_train = X[train_idx]
                Y_train = y[train_idx]
                X_valid = X[valid_idx]
                Y_valid = y[valid_idx]

                clf.fit(X_train, Y_train)

                valid_pred = clf.predict(X_valid)
                recall = recall_score(Y_valid, valid_pred, average='macro')
                f1 = f1_score(Y_valid, valid_pred, average='macro')

                recall_scores[i][j] = recall
                f1_scores[i][j] = f1

                train_pred[valid_idx, i] = valid_pred
                test_pred[:, test_col] = clf.predict(T)
                test_col += 1

                ## Probabilities
                valid_proba = clf.predict_proba(X_valid)
                train_proba[valid_idx, :] = valid_proba
                test_proba += clf.predict_proba(T)

                print("Model- {} and CV- {} recall: {}, f1_score: {}".format(i, j, recall, f1))

            test_proba /= self.n_splits

        return train_proba, test_proba, train_pred, test_pred



# # 调参
# cv = StratifiedKFold(n_splits = 5, shuffle=True, random_state = random_state)
# rdf = RandomForestClassifier(random_state = random_state)
# scoring = {'Recall': make_scorer(recall_score),
#            'f1_score': make_scorer(f1_score)
#           }
#
# params = {'max_depth': [6, 8, 10, 20],
#               'min_samples_split': [5, 10, 15],
#               'min_samples_leaf' : [4, 8, 12],
#               'n_estimators' : [300, 400, 500]
#              }
#
# grid_clf = GridSearchCV(estimator = rdf, param_grid = params, cv = cv, n_jobs=-1, verbose=4)
# grid_clf.fit(x_train, y_train)
# print(grid_clf.best_estimator_)
# print(grid_clf.best_params_)
# class_weight = dict({0:1, 1:14})

rdf = RandomForestClassifier(bootstrap=True, class_weight='balanced',ccp_alpha=0.0,
                       criterion='gini', max_depth=6, max_features='auto',
                       max_leaf_nodes=None, max_samples=None,
                       min_impurity_decrease=0.0, min_impurity_split=None,
                       min_samples_leaf=4, min_samples_split=5,
                       min_weight_fraction_leaf=0.0, n_estimators=300,
                       n_jobs=None, oob_score=False, random_state=random_state,
                       verbose=0, warm_start=False)


# rdf = RandomForestClassifier(bootstrap=True, class_weight='balanced',ccp_alpha=0.0,
#                        criterion='gini', max_depth=20, max_features='auto',
#                        max_leaf_nodes=None, max_samples=None,
#                        min_impurity_decrease=0.0, min_impurity_split=None,
#                        min_samples_leaf=4, min_samples_split=15,
#                        min_weight_fraction_leaf=0.0, n_estimators=400,
#                        n_jobs=None, oob_score=False, random_state=random_state,
#                        verbose=0, warm_start=False)
base_models = [rdf]
n_splits = 5
lgb_stack = Create_ensemble(n_splits = n_splits, base_models = base_models)


train_proba, test_proba, train_pred, test_pred = lgb_stack.predict(x_train, y_train, x_test)


def re_predict(data, threshods):

    argmax = np.argmax(data)

    ## If the argmax is 1 (class-1) then ovbiously return this highest label
    if argmax == 1:
        return argmax

    # If argmax is 0 (class-0) there is a chance that, label is class-1 if
    # the probability of the class is greater than the threshold otherwise obviously
    # return this highest label (class-1)
    elif argmax == 0:
        if data[argmax] >= threshods[argmax] :
            return argmax
        else:
            return (argmax +1)


y = label_binarize(y_train, classes=[0, 1])
_, _, th0 = roc_curve(y[:, 0], train_proba[:, 0])
_, _, th1 = roc_curve(y[:, 0], train_proba[:, 1])
print(np.median(th0))
print(np.median(th1))
threshold = [0.65, 0.34]
new_pred = []
for i in range(train_pred.shape[0]):
    new_pred.append(re_predict(train_proba[i, :], threshold))

print('1. The F-1 score of the model {}\n'.format(f1_score(y_train, new_pred, average='macro')))
print('2. The recall score of the model {}\n'.format(recall_score(y_train, new_pred, average='macro')))
print('3. Classification report \n {} \n'.format(classification_report(y_train, new_pred)))
print('4. Confusion matrix \n {} \n'.format(confusion_matrix(y_train, new_pred)))

# test
test_result = []
for i in range(test_pred.shape[0]):
    test_result.append(re_predict(test_proba[i, :], threshold))

print('1. The F-1 score of the model {}\n'.format(f1_score(y_test, test_result, average='macro')))
print('2. The recall score of the model {}\n'.format(recall_score(y_test, test_result, average='macro')))
print('3. Classification report \n {} \n'.format(classification_report(y_test, test_result)))
print('4. Confusion matrix \n {} \n'.format(confusion_matrix(y_test, test_result)))
