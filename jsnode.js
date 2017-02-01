"use strict";

var babel = require('babel-core');
var yargs = require('yargs');
var vm = require('vm');
var util = require('util');
var es2015 = require('babel-preset-latest-minimal');


function ClientLoop(connection_id, prefix, connection_port) {
    this.connection_id = connection_id;
    this.prefix = prefix
    this.connection_port = connection_port;
    this.process_id = process.pid

    this.console_context = null;
    this.debug = false;
    this.TMP_VAR = '__TMP_DATA';
}


ClientLoop.prototype.getVMSandbox = function () {
    var ret = {
        'console': console,
        'require': require,
        'setTimeout': setTimeout,
        'clearTimeout': clearTimeout,
        'setInterval': setInterval,
        'clearInterval': clearInterval,
        'setImmediate': setImmediate,
        'clearImmediate': clearImmediate
    };
    if (this.is_checking) {
        ret.is_checking = true;
    }
    ret.global = ret;
    return ret;
};

ClientLoop.prototype.getVMContext = function () {
    return vm.createContext(this.getVMSandbox());
};

ClientLoop.prototype.consoleErrorTraceback = function (err) {
    var lines = err.stack.split('\n'),
        i = 0,
        line,
        from_vm = false;

    for (i = 0; i < lines.length; i += 1) {
        line = lines[i].trim();
        if (line.slice(0, 3) === 'at ') {
            if (line.search('evalmachine') !== -1) {
                console.error(lines[i]);
                from_vm = true;
            } else if (this.debug) {
                console.error(lines[i]);
            }
        } else {
            console.error(lines[i]);
        }
    }
    return from_vm;
};


ClientLoop.prototype.getBabelCode = function (code) {
    var result = babel.transform(code, {
        presets: [es2015]
    });
    return result.code
};


ClientLoop.prototype.actionRunCode = function (data) {
    this.vmContext = this.getVMContext();
    this.vmContext['is_checking'] = data.name === '__check__'
    var env_config = data.env_config;
    if (env_config){
        var cover_code = env_config.cover_code;
        if (cover_code){
            this.prepareCoverCode(cover_code);
        }
    }
    var result;
    try {
        result = vm.runInContext(this.getBabelCode(data.code), this.vmContext);
    } catch (err) {
        this.consoleErrorTraceback(err);
        return {
            'do': 'run_fail'
        };
    }
    return {
        'do': 'done',
        'result': null
    };
};


ClientLoop.prototype.actionRunCodeInConsole = function (data) {
    var result;

    if (this.console_context) {

    } else {
        this.console_context = this.getVMContext();
    }

    try {
        result = vm.runInContext(this.getBabelCode(data.code), this.console_context);
    } catch (err) {
        this.consoleErrorTraceback(err);
        return {
            'do': 'run_fail'
        };
    }
    return {
        'do': 'done',
        'result': JSON.stringify(result)
    };
};


ClientLoop.prototype.actionRunFunction = function (data) {
    var result, var_result;

    if (!(data.func in this.vmContext)) {
        return {
            'do': 'exec_fail',
            'text': 'NoExecFunction'
        }
    }

    try {
        vm.runInContext(this.TMP_VAR + ' = ' + JSON.stringify(data.in), this.vmContext);
        var_result = this.vmContext[this.TMP_VAR];
        delete this.vmContext[this.TMP_VAR];
        result = this.coverCode(this.vmContext[data.func], var_result);
    } catch (err) {
        this.consoleErrorTraceback(err);
        return {
            'do': 'exec_fail'
        };
    }
    return {
        'do': 'exec_done',
        'result': result
    };
};

ClientLoop.prototype.actionStop = function () {
    this.connection.destroy();
};

ClientLoop.prototype.prepareCoverCode = function (code) {
    var context = vm.createContext();
    vm.runInContext(code, context);
    this.coverCode = context.cover;
};

ClientLoop.prototype.actionConfig = function (data) {
    var config = data.env_config;
    if (config.is_checking) {
        this.is_checking = true;
    }
    if (config.cover_code) {
        this.prepareCoverCode(config.cover_code);
    }
    return {
        'status': 'success'
    };
};

ClientLoop.prototype.getCallActions = function () {
    return {
        'run': this.actionRunCode.bind(this),
        'exec': this.actionRunFunction.bind(this),
        'console_run': this.actionRunCodeInConsole.bind(this),
        'stop': this.actionStop.bind(this),
        'config': this.actionConfig.bind(this)
    };
};

ClientLoop.prototype.clientWrite = function (data) {
    this.connection.write(JSON.stringify(data) + '\u0000');
};

ClientLoop.prototype.onClientConnected = function () {
    this.clientWrite({
        'do': 'connect',
        'prefix': this.prefix,
        'id': this.connection_id,
        'pid': this.process_id
    });
};

ClientLoop.prototype.onClientData = function (data) {
    var result = this.callActions[data.do](data);
    if (result) {
        this.clientWrite(result);
    }
};

ClientLoop.prototype.getConnection = function () {
    var net = require('net'),
        client = new net.Socket();
    client.connect(this.connection_port, '127.0.0.1', this.onClientConnected.bind(this));

    (function (loop) {
        var current_command = '';
        client.on('data', function (data) {
            var i = 0,
                iChar;
            data = String(data);
            for (i = 0; i < data.length; i += 1) {
                iChar = data.charAt(i);
                if (iChar === '\u0000') {
                    loop.onClientData(JSON.parse(current_command));
                    current_command = '';
                } else {
                    current_command += iChar;
                }
            }
        });
    }(this));
    return client;
};

ClientLoop.prototype.traceError = function () {
    process.on('uncaughtException', function (err) {
        this.consoleErrorTraceback(err);
    }.bind(this));
};

ClientLoop.prototype.start = function () {
    this.is_checking = false;
    this.callActions = this.getCallActions();
    this.connection = this.getConnection();
    this.traceError();
    process.setgid('nogroup');
    process.setuid('nobody');
    this.coverCode = function cover(func, data, ctx) {
        ctx = ctx || this;
        return func.apply(ctx, [data]);
    };
};

var argv = yargs.argv._;
var client = new ClientLoop(argv[0], argv[1], argv[2]);
client.start();
