function [ I ] = getMorseFiltered0DDiagrams( X, tda )
    if nargin < 2
        init;
    end
    
    %Appproximately sample k uniformly spaced vectors on the
    %unit k-sphere
    %http://mathoverflow.net/questions/24688/efficiently-sampling-points-uniformly-from-the-surface-of-an-n-sphere
    N = size(X, 1);
    k = size(X, 2);
    U = randn(k, k);
    U = U./(repmat(sqrt(sum(U.*U, 1)), [k, 1]));
    I = [];

    for kk = 1:k
        filtDist = X*U(:, kk);
        %Start at the first point touched by the swept hyperplane
        filtDist = filtDist - min(filtDist(:));
        V1 = [(1:N)'; (1:N-1)'];
        V2 = [(1:N)'; (2:N)'];
        D = max(filtDist(V1), filtDist(V2));
        S = [V1 V2 D];
        if nargin < 2
            [~, INew] = rca1mfscm(S, max(D(:)) + 10);
        else
            tda.RCA1({'settingsFile=data/cts.txt', 'supplyDataAs=sparseMatrix', sprintf('distanceBoundOnEdges=%g', max(D(:)) + 10), 'verbose=False'}, S);
            INew = tda.getResultsRCA1(0).getIntervals();
        end
        
        %Exclude the last point because it's [0, -1] due to the fact
        %that there's one connected component
        I = [I; INew(1:end-1, :)];
    end
end