const path = require("path");
const CopyPlugin = require("copy-webpack-plugin");
const BundleAnalyzerPlugin =
    require("webpack-bundle-analyzer").BundleAnalyzerPlugin;

var config = {
    entry: {
        index: "./src/index.js",
    },
    experiments: {
        outputModule: true,
    },
    plugins: [
        new CopyPlugin({
            patterns: [
                {
                    from: "./src/component.html",
                    to: "component.html",
                    info: { minimized: true },
                },
                { from: "./src/style.css", to: "style.css" },
                { from: "./src/assets/icons", to: "icons" },
            ],
        }),
    ],
    output: {
        filename: "[name]-[contenthash].js",
        path: path.resolve(__dirname, "build"),
        clean: true,
        library: {
            type: "module",
        },
    },
    module: {
        rules: [
            {
                test: /\.css$/i,
                use: ["style-loader", "css-loader"],
            },
            {
                test: /\.(png|svg|jpg|jpeg|gif)$/i,
                type: "asset/resource",
            },
            {
                test: /\.(woff|woff2|eot|ttf|otf)$/i,
                type: "asset/resource",
            },
        ],
    },
    performance: {
        maxAssetSize: 512000,
        maxEntrypointSize: 512000,
    },
};

module.exports = (env, argv) => {
    if (argv.mode == "development") {
        config.devtool = "inline-source-map";
        config.devServer = {
            static: "./build",
            port: 3001,
            compress: true,
        };
        config.optimization = {};
    } else if (argv.mode == "production") {
        config.optimization = {};
    }
    return config;
};
