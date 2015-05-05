%IRDEPTH: 1 means IR, 2 means depth
function [ thisFrame ] = getFrameFnFolder( foldername, ii, IRDEPTH )
    typestr = 'ir';
    if IRDEPTH == 2
        typestr = 'depth';
    end
    if ii == -1
        files = dir([foldername, filesep, typestr, filesep, '*.png']);
        thisFrame = length(files);
    else
        filename = [foldername, filesep, typestr, filesep, sprintf('%s_%.4d.png', typestr, ii)];
        thisFrame = imread(filename);
        if IRDEPTH == 2
            thisFrame = 256*thisFrame(:, :, 2) + thisFrame(:, :, 1);
        end
    end
end