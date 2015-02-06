if 0
[I, J] = meshgrid(-5:40, -5:40);
D = -exp(- (((I-3).^2 + (J-3).^2)/10) ) -1.1*exp(- (((I+3).^2 + (J+3).^2)/10) );
[I0, IGenerators] = morseFiltration2DMex(D);
imagesc(D);
hold on;
for ii = 1:length(IGenerators)
    g = IGenerators{ii} + 1;
    [birthi, birthj] = ind2sub(size(D), g(end));
    plot(birthi, birthj, 'rx');
    [birthi, birthj] = ind2sub(size(D), g(1:end-1));
    plot([birthi birthi(1)], [birthj birthj(1)], 'b');
    scatter(birthi, birthj, 10, 'b', 'fill');
end

end

if 1
init;
load('TestDists.mat');
D2 = fliplr(flipud(D2));

tic
[I11, Generators11] = morseFiltration2DMex(D1);
[I12, Generators12] = morseFiltration2DMex(max(D1(:))-D1);
[I21, Generators21] = morseFiltration2DMex(D2);
[I22, Generators22] = morseFiltration2DMex(max(D2(:))-D2);
toc
%Convert back to 1D
I12 = max(D1(:)) - fliplr(I12);
I22 = max(D2(:)) - fliplr(I22);

subplot(2, 3, 1);
imagesc(D1);
hold on;
for kk = 1:length(Generators11)
   g = Generators11{kk} + 1;
   [birthi, birthj] = ind2sub(size(D1), g(end));
   plot(birthi, birthj, 'kx');
   [geni, genj] = ind2sub(size(D1), g(1:end-1));
   plot([geni geni(1)], [genj genj(1)], 'k');
end
for kk = 1:length(Generators12)
   g = Generators12{kk} + 1;
   [birthi, birthj] = ind2sub(size(D1), g(end));
   plot(birthi, birthj, 'cx');
   [geni, genj] = ind2sub(size(D1), g(1:end-1));
   plot([geni geni(1)], [genj genj(1)], 'c');
end
axis equal;
colormap('jet');
title('Self-Similarity Matrix Original Beat');

subplot(2, 3, 2);
plotpersistencediagram(I11);
title('0D Persistence Diagram');
subplot(2, 3, 3);
plotpersistencediagram(I12);
title('1D Persistence Diagram');

subplot(2, 3, 4);
imagesc(D2);
hold on;
for kk = 1:length(Generators21)
   g = Generators21{kk} + 1;
   [birthi, birthj] = ind2sub(size(D2), g(end));
   plot(birthi, birthj, 'kx');
   [geni, genj] = ind2sub(size(D2), g(1:end-1));
   plot([geni geni(1)], [genj genj(1)], 'k');
end
for kk = 1:length(Generators22)
   g = Generators22{kk} + 1;
   [birthi, birthj] = ind2sub(size(D2), g(end));
   plot(birthi, birthj, 'cx');
   [geni, genj] = ind2sub(size(D2), g(1:end-1));
   plot([geni geni(1)], [genj genj(1)], 'c');
end
axis equal;
colormap('jet');
title('Self-Similarity Matrix Cover Beat');

subplot(2, 3, 5);
plotpersistencediagram(I21);
title('0D Persistence Diagram');
subplot(2, 3, 6);
plotpersistencediagram(I22);
title('1D Persistence Diagram');

figure;
I22 = I12+0.01*randn(size(I12));
IMax = I12;
IMin = I22;
if (size(I22, 1) > size(I12, 1)) 
    IMin = I12;
    IMax = I22;
end

[matchidx, matchdist, D] = getWassersteinDist(IMax, IMin);

plot(I12(:, 1), I12(:, 2), 'r.');
hold on;
plot(I22(:, 1), I22(:, 2), 'b.');
plot([0 max(I22(:))], [0, max(I22(:))], 'r');
for ii = 1:size(IMax, 1)
    m = find(matchidx(ii, :), 1);
    if (m <= size(IMin, 1))
        m = [IMax(ii, :); IMin(m, :)];
        plot(m(:, 1), m(:, 2), 'g');
    end
end

end