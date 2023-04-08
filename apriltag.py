from dataclasses import dataclass
import numpy as np
import cv2
from time import perf_counter
from tagFamilies import Tag36h11class
from qtp import ApriltagQuadThreshParams
from unionfind import Unionfind, unionfind_get_representative, unionfind_get_set_size
from common import max_pool, do_unionfind_first_line, do_unionfind_line2, timeit

@dataclass
class Detector:
    nthreads = 1
    quad_decimate = 2.0
    quad_sigma = 0.0
    refine_edges: bool = True
    decode_sharpening: float = 0.25
    def __post_init__(self):
        self.qtp = ApriltagQuadThreshParams()

    # td->tag_families = zarray_create(sizeof(apriltag_family_t*));

    def detect(self, img: np.ndarray):       
        # step 1 resize
        if (self.quad_sigma != 0.0):
            # // compute a reasonable kernel width by figuring that the
            # // kernel should go out 2 std devs.
            # //
            # // max sigma          ksz
            # // 0.499              1  (disabled)
            # // 0.999              3
            # // 1.499              5
            # // 1.999              7

            sigma = abs(float(self.quad_sigma))

            ksz = int(4 * sigma) # // 2 std devs in each direction
            if ((ksz & 1) == 0):
                ksz += 1

            if (ksz > 1):
                if (self.quad_sigma > 0):
                    # // Apply a blur
                    # image_u8_gaussian_blur(quad_im, sigma, ksz)
                    pass
                else:
                    # // SHARPEN the image by subtracting the low frequency components.
                    # image_u8_t *orig = image_u8_copy(quad_im)
                    # image_u8_gaussian_blur(quad_im, sigma, ksz);
                    pass

                    # for (int y = 0; y < orig->height; y++) {
                    #     for (int x = 0; x < orig->width; x++) {
                    #         int vorig = orig->buf[y*orig->stride + x];
                    #         int vblur = quad_im->buf[y*quad_im->stride + x];

                    #         int v = 2*vorig - vblur;
                    #         if (v < 0)
                    #             v = 0;
                    #         if (v > 255)
                    #             v = 255;

                    #         quad_im->buf[y*quad_im->stride + x] = (uint8_t) v;
                    #     }
                    # }
        # detect
        quad_im = img
        quads = self.apriltag_quad_thresh(quad_im)
        print(len(quads[0]))
        # Step 2. Decode tags from each quad.
        # refine_edge
        winSize = (5, 5)
        zeroZone = (-1, -1)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TermCriteria_COUNT, 40, 0.001)
        quads = [cv2.cornerSubPix(img, quad.astype(np.float32), winSize, zeroZone, criteria) for quad in quads]
        img_color = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        for q in quads:
            for c in q:
                cv2.circle(img_color, np.round(c[0]).astype(np.int32), 5, (0,0,255))
        cv2.imshow("color", img_color)
        cv2.waitKey(0)

        # decode
        pass

    @timeit
    def connected_components(self, threshim: np.ndarray, w: int, h: int):
        uf = Unionfind(w * h)
        
        do_unionfind_first_line(uf, threshim, w)

        for y in range(1, h):
            do_unionfind_line2(uf, threshim, w, y)

        return uf
    @timeit
    def apriltag_quad_thresh(self, im: np.ndarray):
        # step 1. threshold the image, creating the edge image.
        h, w = im.shape[0], im.shape[1]

        threshim = self.threshold(im)
        cv2.imshow("threshim", threshim)
        # find all contours
        (cnts, _) = cv2.findContours(threshim, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        # cnts = [c for c in cnts if  6000 > cv2.contourArea(c) > self.qtp.min_cluster_pixels  and ratio(c, 1.2, 0.8)]
        output = np.zeros((h, w, 3), dtype=np.uint8)
        # cv2.drawContours(output, cnts, -1, (0, 255, 0), 2)

        quads = [] #array of quad including four peak points
        for c in cnts:
            # if (h[3] < 0 and c.shape[0] >= 4):
            if (c.shape[0] >= 4):
                area = cv2.contourArea(c)
                if area > self.qtp.min_cluster_pixels:
                    hull = cv2.convexHull(c)
                    if (area / cv2.contourArea(hull) > 0.8):
                        quad = cv2.approxPolyDP(hull, 8, True)#maximum_area_inscribed
                        if (len(quad) == 4):
                            areaqued = cv2.contourArea(quad)
                            areahull = cv2.contourArea(hull)
                            if areaqued / areahull > 0.8 and areahull >= areaqued:
                                # Calculate the refined corner locations
                                quads.append(quad)
        return quads
        for i, q in enumerate(quads):

            cv2.drawContours(output, [q], -1, np.random.randint(0, 255, 3, np.uint8).tolist(), 2)
            cv2.imshow("cnts", output)
            cv2.waitKey(0)
        

        return


        # step 2. find connected components.
        # labels = cv2.connectedComponents(threshim)
        # Applying threshold
        cv2.imshow("thres", threshim)
        # Apply the Component analysis function
        analysis = timeit(cv2.connectedComponentsWithStats)(threshim,
                                                    4,
                                                    cv2.CV_32S,
                                                    cv2.CCL_GRANA)
        (totalLabels, label_ids, values, centroid) = analysis
        print(values.shape)
        # return
        
        # Initialize a new image to store 
        # all the output components
        output = np.zeros((h, w, 3), dtype=np.uint8)
        
        # Loop through each component
        for i in range(0, totalLabels):
            
            # Area of the component
            area = values[i, cv2.CC_STAT_AREA] 
            
            if (area > self.qtp.min_cluster_pixels):
                componentMask = np.expand_dims((label_ids == i).astype(np.uint8), 2)
                componentMask = np.repeat(componentMask, 3, axis=2) * np.random.randint(0, 255, 3, dtype=np.uint8)
                output = cv2.bitwise_or(output, componentMask)
        
        
                cv2.imshow("Filtered Components", output)
                cv2.waitKey(0)
        return
        uf = self.connected_components(threshim, w, h)
        # make segmentation image.
        if (True):
            d = np.zeros((h, w, 3), np.uint8)
            colors = np.zeros((h*w, 3), np.uint8)

            for y in range(h):
                for x in range(w):
                    v = unionfind_get_representative(uf, y*w+x)

                    if (unionfind_get_set_size(uf, v) < self.qtp.min_cluster_pixels):
                        continue

                    color = colors[v]
                    r = color[0]
                    g = color[1]
                    b = color[2]

                    if (r == 0 and g == 0 and b == 0):
                        r, g, b = colors[v] = np.random.randint(0, 150, 3)

                    d[y, x, 0] = r
                    d[y, x, 1] = g
                    d[y, x, 2] = b

            cv2.imwrite("debug.png", d)
        # print(uf.data)

        # clusters = gradient_clusters(td, threshim, w, h, ts, uf);

        # # step 3. process each connected component.

        # zarray_t* quads = fit_quads(td, w, h, clusters, im);

        # for (int i = 0; i < zarray_size(clusters); i++) {
        #     zarray_t *cluster;
        #     zarray_get(clusters, i, &cluster);
        #     zarray_destroy(cluster);
        # }

        # return quads;

    @timeit
    def threshold(self, im: np.ndarray) -> np.ndarray:
        w = im.shape[1]
        h = im.shape[0]
        
        assert(w < 32768)
        assert(h < 32768)

        threshim = np.zeros((h, w), dtype=np.uint8)
        # assert(threshim->stride == s);

        # The idea is to find the maximum and minimum values in a
        # window around each pixel. If it's a contrast-free region
        # (max-min is small), don't try to binarize. Otherwise,
        # threshold according to (max+min)/2.
        #
        # Mark low-contrast regions with value 127 so that we can skip
        # future work on these areas too.

        # however, computing max/min around every pixel is needlessly
        # expensive. We compute max/min for tiles. To avoid artifacts
        # that arise when high-contrast features appear near a tile
        # edge (and thus moving from one tile to another results in a
        # large change in max/min value), the max/min values used for
        # any pixel are computed from all 3x3 surrounding tiles. Thus,
        # the max/min sampling area for nearby pixels overlap by at least
        # one tile.
        #
        # The important thing is that the windows be large enough to
        # capture edge transitions; the tag does not need to fit into
        # a tile.

        # XXX Tunable. Generally, small tile sizes--- so long as they're
        # large enough to span a single tag edge--- seem to be a winner.
        tilesz = 4

        # the last (possibly partial) tiles along each row and column will
        # just use the min/max value from the last full tile.
        tw = w // tilesz
        th = h // tilesz

        #  first, collect min/max statistics for each tile
        im_max = max_pool(im, tilesz, True)
        im_min = max_pool(im, tilesz, False)

        # second, apply 3x3 max/min convolution to "blur" these values
        # over larger areas. This reduces artifacts due to abrupt changes
        # in the threshold value.
        if True:
            kernel = np.ones((3, 3), dtype=np.uint8)
            im_max = cv2.dilate(im_max, kernel)
            im_min = cv2.erode(im_min, kernel)
        im_min = np.repeat(np.repeat(im_min, tilesz, axis=1), tilesz, axis=0)
        im_max = np.repeat(np.repeat(im_max, tilesz, axis=1), tilesz, axis=0)
        
        im_diff = im_max - im_min
        threshim = np.where( im_diff < self.qtp.min_white_black_diff, np.uint8(127),
                            np.where( im > (im_min + im_diff // 2), np.uint8(255), np.uint8(0)))
        # threshim = np.where( im_diff < self.qtp.min_white_black_diff, np.uint8(0), im)
        # debug
        # print(threshim.dtype)
        # print(im_diff.shape)
        # print(im.shape)
        # cv2.imshow("tt", threshim)
        # cv2.waitKey(0)

        # # we skipped over the non-full-sized tiles above. Fix those now.
        # if True:
        #     for (int y = 0; y < h; y++) {

        #         # what is the first x coordinate we need to process in this row?

        #         int x0;

        #         if (y >= th*tilesz) {
        #             x0 = 0; // we're at the bottom; do the whole row.
        #         } else {
        #             x0 = tw*tilesz; // we only need to do the right most part.
        #         }

        #         // compute tile coordinates and clamp.
        #         int ty = y / tilesz;
        #         if (ty >= th)
        #             ty = th - 1;

        #         for (int x = x0; x < w; x++) {
        #             int tx = x / tilesz;
        #             if (tx >= tw)
        #                 tx = tw - 1;

        #             int max = im_max[ty*tw + tx];
        #             int min = im_min[ty*tw + tx];
        #             int thresh = min + (max - min) / 2;

        #             uint8_t v = im->buf[y*s+x];
        #             if (v > thresh)
        #                 threshim->buf[y*s+x] = 255;
        #             else
        #                 threshim->buf[y*s+x] = 0;
        #         }
        #     }
        # }

        return threshim